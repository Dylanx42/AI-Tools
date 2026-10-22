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
          @"quota": @{@"weeklyPercent": @2, @"weeklyResetAt": @1800600000},
          @"quotaRefresh": @{@"status": @"ok"}}
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
    NSMutableDictionary *unconfirmed = [FixtureRows()[1] mutableCopy];
    [unconfirmed removeObjectForKey:@"quotaRefresh"];
    QuotaAccount *readable = QuotaParseAccounts(JSON(@{@"accounts": @[unconfirmed]}), nil).firstObject;
    Check(!readable.refreshError && !readable.snapshot.upstreamRefreshConfirmed && readable.snapshot.secondary.remainingPercent == 98,
          @"Absent optional refresh outcome still allows quota display without claiming freshness");
    Check([QuotaReadStatus(readable.snapshot, NO, nil) containsString:@"上游状态未提供"] &&
          ![QuotaReadStatus(readable.snapshot, NO, nil) containsString:@"失败"], @"Missing refresh metadata is a neutral reading state");
    unconfirmed[@"quotaRefresh"] = @{@"status": @"not_reported"};
    readable = QuotaParseAccounts(JSON(@{@"accounts": @[unconfirmed]}), nil).firstObject;
    Check(!readable.refreshError && !readable.snapshot.upstreamRefreshConfirmed, @"Explicitly unreported status is also neutral");
    Check(accounts[0].snapshot.upstreamRefreshConfirmed && !accounts[0].refreshError,
          @"Explicit ok still confirms upstream freshness");
    Check([QuotaReadStatus(accounts[0].snapshot, NO, QuotaError(QuotaErrorTimedOut, @"timeout")) containsString:@"失败"],
          @"Real read failure still has an error presentation");
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
@property(nonatomic, copy) QuotaResetCreditsCompletion pendingCredits;
@property(nonatomic, copy) NSString *creditAccountID;
@end
@implementation StubQuotaService
- (void)fetch:(QuotaAccountsCompletion)completion { self.pending = completion; }
- (void)fetchResetCreditsForAccountID:(NSString *)accountID completion:(QuotaResetCreditsCompletion)completion {
    self.creditAccountID = accountID;
    self.pendingCredits = completion;
}
- (void)cancel {} // Keep delayed callbacks available to test the controller's generation guards.
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
    StubQuotaService *creditService = [StubQuotaService new];
    app.service = service;
    app.resetCreditService = creditService;
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
    Check([creditService.creditAccountID isEqual:@"test-pro"], @"Reset-credit query targets the monitored account");
    QuotaResetCreditsCompletion delayedPro = creditService.pendingCredits;
    NSURL *proFile = app.historyFileURL;
    NSData *before = [NSData dataWithContentsOfURL:proFile];
    [app refresh];
    service.pending(nil, QuotaError(QuotaErrorProtocol, @"service offline"));
    Check(app.lastError && [[NSData dataWithContentsOfURL:proFile] isEqual:before], @"Failed refresh preserves data without appending history");

    NSMenuItem *choice = [[NSMenuItem alloc] initWithTitle:@"plus" action:nil keyEquivalent:@""];
    choice.representedObject = @"test-main";
    [app selectMonitoredAccount:choice];
    Check([app.selectedAccountID isEqual:@"test-main"] && ![app.historyFileURL isEqual:proFile], @"Manual selection changes history files");
    QuotaResetCredits *proCredits = QuotaParseResetCredits(JSON(@{@"available_count": @9}), @"test-pro", nil);
    delayedPro(proCredits, nil);
    Check(!app.resetCredits && !app.resetCreditsLoading, @"Late old-account coupon result cannot appear after selection");
    Check(app.historyPoints.count == 0, @"New account starts with its own empty chart");
    // Changing selection during a request must not relabel an in-flight response.
    choice.representedObject = @"test-pro";
    [app selectMonitoredAccount:choice];
    Check([app.selectedAccountID isEqual:@"test-main"], @"Account selection is held while a request is in flight");
    service.pending(accounts, nil);
    Check(app.snapshot.primary.remainingPercent == 77 && app.historyPoints.count == 1, @"Selected account records its own sample");
    Check([creditService.creditAccountID isEqual:@"test-main"], @"Coupon query follows the new monitoring choice");
    QuotaResetCredits *mainCredits = QuotaParseResetCredits(JSON(@{@"available_count": @2}), @"test-main", nil);
    creditService.pendingCredits(mainCredits, nil);
    Check(app.resetCredits.availableCount.integerValue == 2 && !app.resetCreditsError, @"Monitored account coupon count is displayed");
    QuotaSnapshot *currentQuota = app.snapshot;
    [app refreshResetCredits];
    creditService.pendingCredits(nil, QuotaError(QuotaErrorProtocol, @"coupon unavailable"));
    Check(!app.resetCredits && app.resetCreditsError && app.snapshot == currentQuota,
          @"Coupon failure becomes unknown without breaking quota presentation");
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
    NSMutableDictionary *unconfirmedRow = [FixtureRows()[0] mutableCopy];
    [unconfirmedRow removeObjectForKey:@"quotaRefresh"];
    unconfirmedRow[@"quota"] = @{@"weeklyPercent": @40};
    service.pending(QuotaParseAccounts(JSON(@{@"accounts": @[unconfirmedRow]}), nil), nil);
    Check(!app.lastError && app.consecutiveFailures == 0 && app.lastRefreshCompletedAt &&
          app.snapshot.secondary.remainingPercent == 60 && !app.snapshot.upstreamRefreshConfirmed,
          @"Successful CLI read with absent metadata updates display and is not put into failure backoff");
    Check([[NSData dataWithContentsOfURL:mainFile] isEqual:mainBefore],
          @"Readable but unconfirmed quota is still not recorded as a fresh sample");
    unconfirmedRow[@"quotaRefresh"] = @{@"status": @"ok"};
    [app refresh];
    service.pending(QuotaParseAccounts(JSON(@{@"accounts": @[unconfirmedRow]}), nil), nil);
    Check(!app.lastError && app.snapshot.upstreamRefreshConfirmed &&
          ![[NSData dataWithContentsOfURL:mainFile] isEqual:mainBefore],
          @"Affirmative refresh resumes history after metadata was previously absent");
    [app refresh];
    service.pending(@[accounts[1]], nil);
    Check(!app.snapshot && !app.historyFileURL && !app.historyPoints.count && [app.selectedAccountID isEqual:@"test-main"],
          @"Removed monitored account clears presentation and retains explicit selection");
    Check([[NSString stringWithContentsOfURL:legacy encoding:NSUTF8StringEncoding error:nil] isEqual:@"legacy history stays here\n"],
          @"Legacy history is never assigned or overwritten");
    [app.timer invalidate];
    [app.preferences removePersistentDomainForName:suite];
}

static void TestResetCreditsMapping(void) {
    NSArray *rows = @[
        @{@"granted_at": @"2020-01-01T00:00:00Z", @"expires_at": @"2099-03-02T10:00:00.000Z"},
        @{@"granted_at": @"2020-01-01T00:00:00Z", @"expires_at": @"2099-02-01T10:00:00Z"}
    ];
    QuotaResetCredits *credits = QuotaParseResetCredits(JSON(@{@"available_count": @2, @"credits": rows}), @"test-pro", nil);
    Check(credits.availableCount.integerValue == 2 && credits.expiries.count == 2 && [credits.accountID isEqual:@"test-pro"],
          @"Coupon count and ISO timestamps belong to the requested account");
    Check([credits.expiries[0] compare:credits.expiries[1]] == NSOrderedAscending, @"Nearest coupon expiry comes first");
    Check([QuotaResetCreditsText(credits, NO, nil) containsString:@"最近"], @"Multiple coupons show nearest expiry");
    QuotaResetCredits *listOnly = QuotaParseResetCredits(JSON(@{@"credits": rows}), @"test-main", nil);
    Check(listOnly.availableCount.integerValue == 2, @"Complete credit list supplies count when summary is absent");
    QuotaResetCredits *zero = QuotaParseResetCredits(JSON(@{@"available_count": @0, @"credits": @[]}), @"test-main", nil);
    Check(zero && zero.availableCount.integerValue == 0 && [QuotaResetCreditsText(zero, NO, nil) isEqual:@"重置券 0 张"],
          @"Confirmed zero is shown distinctly from unavailable data");
    QuotaResetCredits *countOnly = QuotaParseResetCredits(JSON(@{@"available_count": @3}), @"test-main", nil);
    Check(countOnly.availableCount.integerValue == 3 && [QuotaResetCreditsText(countOnly, NO, nil) containsString:@"到期时间暂无数据"],
          @"Known count is preserved without inventing expiry");
    Check(!QuotaParseResetCredits(JSON(@{}), @"test-main", nil), @"Missing payload cannot become zero coupons");
    Check(!QuotaParseResetCredits(JSON(@{@"available_count": @YES}), @"test-main", nil), @"Boolean count is rejected");
    Check(!QuotaParseResetCredits(JSON(@{@"available_count": @(-1)}), @"test-main", nil), @"Negative count is rejected");
    Check(!QuotaParseResetCredits(JSON(@{@"credits": @[@{@"expires_at": @"invalid"}]}), @"test-main", nil),
          @"Malformed list cannot imply zero coupons");
    QuotaResetCredits *expired = QuotaParseResetCredits(JSON(@{@"credits": @[
        @{@"granted_at": @"2000-01-01T00:00:00Z", @"expires_at": @"2001-01-01T00:00:00Z"}]}), @"test-main", nil);
    Check(expired.availableCount.integerValue == 0 && !expired.expiries.count, @"Expired coupons are not counted as available");
    Check([QuotaResetCreditsText(nil, NO, QuotaError(QuotaErrorProtocol, @"failed")) isEqual:@"重置券 暂不可用"],
          @"Failed lookup is unavailable rather than zero");
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

static void TestResetCreditsCLI(NSURL *directory) {
    NSURL *valid = MakeExecutable(directory, @"mock-reset-ocx",
        @"[ \"$*\" = 'account reset-credits test-pro --json' ] || exit 17\nprintf '{\"available_count\":2,\"credits\":[]}'\n");
    OpenCodexQuotaService *service = [[OpenCodexQuotaService alloc] initWithExecutableURL:valid timeout:2];
    __block BOOL done = NO;
    [service fetchResetCreditsForAccountID:@"test-pro" completion:^(QuotaResetCredits *credits, NSError *error) {
        Check(NSThread.isMainThread && !error && credits.availableCount.integerValue == 2 && [credits.accountID isEqual:@"test-pro"],
              @"Real subprocess uses the exact inspection command, without consume flags");
        done = YES;
    }];
    NSDate *deadline = [NSDate dateWithTimeIntervalSinceNow:5];
    while (!done && deadline.timeIntervalSinceNow > 0) [NSRunLoop.mainRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.01]];
    Check(done, @"Coupon inspection completes");
    done = NO;
    [service fetchResetCreditsForAccountID:@"--consume" completion:^(QuotaResetCredits *credits, NSError *error) {
        Check(!credits && error.code == QuotaErrorAccountUnavailable, @"Option-shaped account identity cannot become a CLI flag");
        done = YES;
    }];
    [NSRunLoop.mainRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.05]];
    Check(done, @"Invalid inspection identity is rejected");
}

int main(void) {
    @autoreleasepool {
        NSURL *directory = [[NSURL fileURLWithPath:NSTemporaryDirectory() isDirectory:YES]
                            URLByAppendingPathComponent:NSUUID.UUID.UUIDString isDirectory:YES];
        [NSFileManager.defaultManager createDirectoryAtURL:directory withIntermediateDirectories:YES
                                                attributes:@{NSFilePosixPermissions: @0700} error:nil];
        TestMapping();
        TestResetCreditsMapping();
        TestControllerAndHistory(directory);
        TestCLI(directory);
        TestResetCreditsCLI(directory);
        [NSFileManager.defaultManager removeItemAtURL:directory error:nil];
        puts("PASS: OpenCodex quota/reset-credit mapping, account selection, late-response isolation, history, observational CLI, failures, timeout and cancellation");
    }
    return 0;
}
