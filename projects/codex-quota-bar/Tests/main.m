// Include the UI's history/controller implementation without starting its application.
#define main QuotaApplicationMain
#import "../Sources/main.m"
#undef main

static void Check(BOOL condition, NSString *message) {
    if (!condition) { fprintf(stderr, "FAIL: %s\n", message.UTF8String); exit(1); }
}

static NSData *JSON(id object) {
    return [NSJSONSerialization dataWithJSONObject:object options:0 error:nil];
}

static NSArray *FixtureRows(void) {
    // Synthetic values only; no user emails, account IDs, tokens or quota dumps.
    return @[
        @{@"id": @"test-main", @"type": @"codex", @"label": @"plus", @"active": @NO,
          @"quota": @{@"shortPercent": @23, @"shortWindowSeconds": @18000,
                     @"shortResetAt": @1800000000, @"weeklyPercent": @4, @"weeklyResetAt": @1800600000},
          @"quotaRefresh": @{@"status": @"ok"}},
        @{@"id": @"test-pro", @"type": @"codex", @"label": @"pro", @"active": @YES,
          @"quota": @{@"weeklyPercent": @2, @"weeklyResetAt": @1800600000}}
    ];
}

static NSArray<QuotaAccount *> *FixtureAccounts(void) {
    return QuotaParseAccounts(JSON(@{@"accounts": FixtureRows()}), nil);
}

static void TestMapping(void) {
    NSArray<QuotaAccount *> *accounts = FixtureAccounts();
    Check(accounts.count == 2, @"Both Codex accounts are selectable");
    Check(accounts[0].snapshot.primary.remainingPercent == 77 && accounts[0].snapshot.secondary.remainingPercent == 96,
          @"Used percentages must be converted to remaining percentages");
    Check(accounts[1].snapshot.primary == nil && accounts[1].snapshot.secondary.remainingPercent == 98,
          @"Absent short window is unknown, not 100 percent");
    Check(QuotaSelectedAccount(accounts, nil) == accounts[1], @"Initial choice uses active OpenCodex account");
    Check(QuotaSelectedAccount(accounts, @"test-main") == accounts[0], @"Saved choice stays fixed when active differs");
    Check(QuotaSelectedAccount(accounts, @"removed") == nil, @"Removed choice cannot silently fall back");

    NSDictionary *monthly = @{@"id": @"monthly", @"type": @"codex",
                              @"quota": @{@"monthlyPercent": @100, @"monthlyResetAt": @1800000000}};
    QuotaAccount *month = QuotaParseAccounts(JSON(@{@"accounts": @[monthly]}), nil).firstObject;
    Check(month.snapshot.secondary.durationMinutes == 43200 && month.snapshot.secondary.remainingPercent == 0,
          @"Monthly fallback and exhausted quota remain distinct from unknown");
    NSDictionary *badQuota = @{@"id": @"bad", @"type": @"codex", @"quota": @{@"shortPercent": @YES, @"weeklyPercent": @101}};
    QuotaAccount *bad = QuotaParseAccounts(JSON(@{@"accounts": @[badQuota]}), nil).firstObject;
    Check(!bad.snapshot.primary && !bad.snapshot.secondary && bad.refreshError, @"Invalid percentages never become quota");
    NSDictionary *noReset = @{@"id": @"no-reset", @"type": @"codex", @"quota": @{@"fiveHourPercent": @0}};
    QuotaAccount *known = QuotaParseAccounts(JSON(@{@"accounts": @[noReset]}), nil).firstObject;
    Check(known.snapshot.primary.remainingPercent == 100 && !known.snapshot.primary.resetsAt,
          @"An actual zero used value is valid even if reset time is missing");
    NSMutableDictionary *stale = [FixtureRows()[0] mutableCopy];
    stale[@"quotaRefresh"] = @{@"status": @"timeout"};
    Check(QuotaParseAccounts(JSON(@{@"accounts": @[stale]}), nil).firstObject.refreshError != nil,
          @"A stale quota cache is explicitly marked");
    stale[@"quotaRefresh"] = @{@"status": @"ok"};
    stale[@"needsReauth"] = @YES;
    Check(QuotaParseAccounts(JSON(@{@"accounts": @[stale]}), nil).firstObject.refreshError != nil,
          @"Expired login is not a successful refresh");
    NSError *error = nil;
    Check(!QuotaParseAccounts(JSON(@{@"accounts": @[FixtureRows()[0], FixtureRows()[0]]}), &error) && error,
          @"Duplicate account identities reject ambiguous data");
    Check(!QuotaParseAccounts([@"invalid json" dataUsingEncoding:NSUTF8StringEncoding], nil), @"Malformed JSON is rejected");
    Check(!QuotaParseAccounts(JSON(@{@"accounts": @"wrong type"}), nil), @"Malformed envelope is rejected");
    Check(QuotaParseAccounts(JSON(@{@"accounts": @[]}), nil).count == 0, @"Empty account pool is valid");
    Check(![QuotaHistoryFileName(@"../escape") containsString:@"/"] &&
          ![QuotaHistoryFileName(@"test-main") isEqual:QuotaHistoryFileName(@"test-pro")],
          @"History names are separate and cannot escape their directory");
}

@interface StubQuotaService : OpenCodexQuotaService
@property(nonatomic, copy) QuotaAccountsCompletion pending;
@end
@implementation StubQuotaService
- (void)fetch:(QuotaAccountsCompletion)completion { self.pending = completion; }
@end

// No menu-bar registration or window server is needed for controller regression checks.
@interface HeadlessDelegate : AppDelegate
@end
@implementation HeadlessDelegate
- (void)updateStatusDisplay {}
- (void)rebuildMenu {}
@end

static void TestControllerAndHistory(NSURL *directory) {
    HeadlessDelegate *app = [HeadlessDelegate new];
    StubQuotaService *service = [StubQuotaService new];
    app.service = service;
    NSString *suite = [@"quota-tests." stringByAppendingString:NSUUID.UUID.UUIDString];
    app.preferences = [[NSUserDefaults alloc] initWithSuiteName:suite];
    app.selectedAccountID = nil;
    app.historyDirectoryURL = [directory URLByAppendingPathComponent:@"accounts" isDirectory:YES];
    NSURL *legacy = [directory URLByAppendingPathComponent:@"quota-history.csv"];
    [@"legacy history stays here\n" writeToURL:legacy atomically:YES encoding:NSUTF8StringEncoding error:nil];
    NSArray<QuotaAccount *> *accounts = FixtureAccounts();
    [app refresh];
    service.pending(accounts, nil);
    Check([app.selectedAccountID isEqual:@"test-pro"], @"Controller initially selects active account");
    Check([[app.preferences stringForKey:QuotaSelectedAccountKey] isEqual:@"test-pro"], @"Selection is persisted");
    NSURL *proFile = app.historyFileURL;
    NSData *before = [NSData dataWithContentsOfURL:proFile];
    [app refresh];
    service.pending(nil, QuotaError(QuotaErrorProtocol, @"service offline"));
    Check(app.lastError && [[NSData dataWithContentsOfURL:proFile] isEqual:before], @"Failed refresh preserves data without appending history");

    NSMenuItem *choice = [[NSMenuItem alloc] initWithTitle:@"plus" action:nil keyEquivalent:@""];
    choice.representedObject = @"test-main";
    [app selectMonitoredAccount:choice];
    Check([app.selectedAccountID isEqual:@"test-main"] && ![app.historyFileURL isEqual:proFile], @"Manual selection changes history files");
    Check(app.historyPoints.count == 0, @"New account starts with its own empty chart");
    // Changing selection during a request must not relabel an in-flight response.
    choice.representedObject = @"test-pro";
    [app selectMonitoredAccount:choice];
    Check([app.selectedAccountID isEqual:@"test-main"], @"Account selection is held while a request is in flight");
    service.pending(accounts, nil);
    Check(app.snapshot.primary.remainingPercent == 77 && app.historyPoints.count == 1, @"Selected account records its own sample");
    NSURL *mainFile = app.historyFileURL;
    NSData *mainBefore = [NSData dataWithContentsOfURL:mainFile];
    [app recordSnapshotIfChanged:accounts[1].snapshot];
    Check([[NSData dataWithContentsOfURL:mainFile] isEqual:mainBefore], @"Foreign-account snapshot cannot enter history");
    [app refresh];
    NSMutableArray<QuotaAccount *> *stale = [FixtureAccounts() mutableCopy];
    stale[0].refreshError = QuotaError(QuotaErrorAccountUnavailable, @"cached");
    service.pending(stale, nil);
    Check(app.lastError && [[NSData dataWithContentsOfURL:mainFile] isEqual:mainBefore], @"Cached refresh does not create a fresh sample");
    [app refresh];
    service.pending(@[accounts[1]], nil);
    Check(!app.snapshot && !app.historyFileURL && !app.historyPoints.count && [app.selectedAccountID isEqual:@"test-main"],
          @"Removed monitored account clears presentation and retains explicit selection");
    Check([[NSString stringWithContentsOfURL:legacy encoding:NSUTF8StringEncoding error:nil] isEqual:@"legacy history stays here\n"],
          @"Legacy history is never assigned or overwritten");
    [app.timer invalidate];
    [app.preferences removePersistentDomainForName:suite];
}

static NSURL *MakeExecutable(NSURL *directory, NSString *name, NSString *body) {
    NSURL *url = [directory URLByAppendingPathComponent:name];
    [[@"#!/bin/sh\n" stringByAppendingString:body] writeToURL:url atomically:YES encoding:NSUTF8StringEncoding error:nil];
    [NSFileManager.defaultManager setAttributes:@{NSFilePosixPermissions: @0700} ofItemAtPath:url.path error:nil];
    return url;
}

static void AwaitFetch(OpenCodexQuotaService *service, BOOL expectSuccess, NSInteger expectedError) {
    __block BOOL done = NO;
    __block NSInteger calls = 0;
    [service fetch:^(NSArray<QuotaAccount *> *accounts, NSError *error) {
        calls++;
        Check(NSThread.isMainThread, @"CLI completion is delivered on main thread");
        Check(expectSuccess ? accounts.count == 2 && !error : !accounts && error.code == expectedError,
              @"CLI result/deadline matches expectation");
        done = YES;
    }];
    NSDate *deadline = [NSDate dateWithTimeIntervalSinceNow:5];
    while (!done && deadline.timeIntervalSinceNow > 0) [NSRunLoop.mainRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.01]];
    Check(done && calls == 1, @"CLI always completes within deadline exactly once");
    [NSRunLoop.mainRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.05]];
    Check(calls == 1, @"Late process exit cannot complete twice");
}

static void TestCLI(NSURL *directory) {
    NSString *json = [[NSString alloc] initWithData:JSON(@{@"accounts": FixtureRows()}) encoding:NSUTF8StringEncoding];
    NSURL *valid = MakeExecutable(directory, @"mock-ocx", [NSString stringWithFormat:
        @"[ \"$*\" = 'account list openai --quota --refresh --json' ] || exit 17\ncat <<'QUOTA_JSON'\n%@\nQUOTA_JSON\n", json]);
    AwaitFetch([[OpenCodexQuotaService alloc] initWithExecutableURL:valid timeout:2], YES, 0);
    NSURL *bad = MakeExecutable(directory, @"invalid-ocx", @"printf 'invalid json'\n");
    AwaitFetch([[OpenCodexQuotaService alloc] initWithExecutableURL:bad timeout:2], NO, QuotaErrorProtocol);
    NSURL *failure = MakeExecutable(directory, @"failed-ocx", @"printf 'private diagnostic' >&2\nexit 1\n");
    AwaitFetch([[OpenCodexQuotaService alloc] initWithExecutableURL:failure timeout:2], NO, QuotaErrorProtocol);
    NSURL *oversized = MakeExecutable(directory, @"oversized-ocx", @"exec /usr/bin/head -c 2097153 /dev/zero\n");
    AwaitFetch([[OpenCodexQuotaService alloc] initWithExecutableURL:oversized timeout:2], NO, QuotaErrorProtocol);
    NSURL *slow = MakeExecutable(directory, @"slow-ocx", @"exec /bin/sleep 10\n");
    AwaitFetch([[OpenCodexQuotaService alloc] initWithExecutableURL:slow timeout:0.1], NO, QuotaErrorTimedOut);
    AwaitFetch([[OpenCodexQuotaService alloc] initWithExecutableURL:[directory URLByAppendingPathComponent:@"missing"] timeout:1], NO, QuotaErrorCLIUnavailable);
    OpenCodexQuotaService *cancelled = [[OpenCodexQuotaService alloc] initWithExecutableURL:slow timeout:0.2];
    __block BOOL callback = NO;
    [cancelled fetch:^(NSArray *accounts, NSError *error) { callback = YES; }];
    [cancelled cancel];
    [NSRunLoop.mainRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.3]];
    Check(!callback, @"Cancelled work cannot deliver stale results");
}

int main(void) {
    @autoreleasepool {
        NSURL *directory = [[NSURL fileURLWithPath:NSTemporaryDirectory() isDirectory:YES]
                            URLByAppendingPathComponent:NSUUID.UUID.UUIDString isDirectory:YES];
        [NSFileManager.defaultManager createDirectoryAtURL:directory withIntermediateDirectories:YES
                                                attributes:@{NSFilePosixPermissions: @0700} error:nil];
        TestMapping();
        TestControllerAndHistory(directory);
        TestCLI(directory);
        [NSFileManager.defaultManager removeItemAtURL:directory error:nil];
        puts("PASS: OpenCodex mapping, account selection, history isolation, CLI failures, timeout and cancellation");
    }
    return 0;
}
