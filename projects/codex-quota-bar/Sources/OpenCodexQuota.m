#import "OpenCodexQuota.h"
#import <CommonCrypto/CommonDigest.h>
#import <math.h>
#import <signal.h>

NSString *const QuotaErrorDomain = @"app.codexquotabar.desktop";

NSError *QuotaError(QuotaErrorCode code, NSString *description) {
    return [NSError errorWithDomain:QuotaErrorDomain code:code
                          userInfo:@{NSLocalizedDescriptionKey: description}];
}

@implementation QuotaWindow
- (NSInteger)remainingPercent { return MAX(0, MIN(100, 100 - self.usedPercent)); }
@end
@implementation QuotaSnapshot
@end
@implementation QuotaAccount
@end

static NSString *QuotaString(id value) {
    return [value isKindOfClass:NSString.class] && [value length] > 0 ? value : nil;
}

static NSNumber *QuotaNumber(id value) {
    if (![value isKindOfClass:NSNumber.class] || CFGetTypeID((__bridge CFTypeRef)value) == CFBooleanGetTypeID()) return nil;
    return isfinite([value doubleValue]) ? value : nil;
}

static QuotaWindow *QuotaParseWindow(NSDictionary *quota, NSString *percentKey,
                                    NSString *resetKey, NSInteger minutes) {
    NSNumber *percent = QuotaNumber(quota[percentKey]);
    if (!percent || percent.doubleValue < 0 || percent.doubleValue > 100) return nil;
    QuotaWindow *window = [QuotaWindow new];
    window.usedPercent = (NSInteger)llround(percent.doubleValue);
    window.durationMinutes = minutes;
    NSNumber *reset = QuotaNumber(quota[resetKey]);
    if (reset.doubleValue > 0) window.resetsAt = [NSDate dateWithTimeIntervalSince1970:reset.doubleValue];
    return window;
}

NSArray<QuotaAccount *> *QuotaParseAccounts(NSData *data, NSError **error) {
    id root = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
    if (![root isKindOfClass:NSDictionary.class] || ![root[@"accounts"] isKindOfClass:NSArray.class]) {
        if (error) *error = QuotaError(QuotaErrorProtocol, @"OpenCodex 未返回账户列表，请确认 ocx account list openai --quota --refresh --json 可以正常执行。");
        return nil;
    }
    NSMutableArray<QuotaAccount *> *accounts = [NSMutableArray array];
    NSMutableSet<NSString *> *identifiers = [NSMutableSet set];
    for (id value in root[@"accounts"]) {
        if (![value isKindOfClass:NSDictionary.class] || !QuotaString(value[@"id"]) ||
            ![value[@"type"] isEqual:@"codex"] || [identifiers containsObject:value[@"id"]]) {
            if (error) *error = QuotaError(QuotaErrorProtocol, @"OpenCodex 账户列表格式异常，或 openai 尚未使用 ChatGPT/Codex 登录账户。");
            return nil;
        }
        NSDictionary *row = value;
        QuotaAccount *account = [QuotaAccount new];
        account.accountID = row[@"id"];
        [identifiers addObject:account.accountID];
        NSString *plan = QuotaString(row[@"plan"]);
        NSString *label = QuotaString(row[@"label"]) ?: plan ?: @"Codex 账户";
        // The CLI already applies OpenCodex's email masking policy. Keep it in memory only.
        NSString *email = QuotaString(row[@"email"]);
        account.displayName = email ? [NSString stringWithFormat:@"%@ · %@", label, email] :
            [NSString stringWithFormat:@"%@ · %@", label, account.accountID];
        account.active = [row[@"active"] isEqual:@YES];
        NSDictionary *quota = [row[@"quota"] isKindOfClass:NSDictionary.class] ? row[@"quota"] : @{};
        QuotaSnapshot *snapshot = [QuotaSnapshot new];
        snapshot.accountID = account.accountID;
        snapshot.planType = plan;
        snapshot.updatedAt = NSDate.date; // CLI read time; not an upstream observation timestamp.
        snapshot.primary = QuotaParseWindow(quota, @"fiveHourPercent", @"fiveHourResetAt", 300);
        if (!snapshot.primary) {
            NSNumber *seconds = QuotaNumber(quota[@"shortWindowSeconds"]);
            NSInteger minutes = seconds.doubleValue >= 60 && seconds.doubleValue <= 31 * 86400
                ? (NSInteger)(seconds.doubleValue / 60) : 300;
            snapshot.primary = QuotaParseWindow(quota, @"shortPercent", @"shortResetAt", minutes);
        }
        snapshot.secondary = QuotaParseWindow(quota, @"weeklyPercent", @"weeklyResetAt", 7 * 1440);
        if (!snapshot.secondary) snapshot.secondary = QuotaParseWindow(quota, @"monthlyPercent", @"monthlyResetAt", 30 * 1440);
        // A known account can have no quota yet. Keep the row so it remains selectable.
        account.snapshot = snapshot;
        NSDictionary *refresh = [row[@"quotaRefresh"] isKindOfClass:NSDictionary.class] ? row[@"quotaRefresh"] : @{};
        NSString *status = QuotaString(refresh[@"status"]);
        NSString *problem = nil;
        if ([row[@"needsReauth"] isEqual:@YES]) problem = @"该账户需要在 OpenCodex 中重新登录。";
        else if ([row[@"paused"] isEqual:@YES]) problem = @"该账户已在 OpenCodex 中暂停，显示的额度可能是缓存。";
        else if (status && ![status isEqualToString:@"ok"]) problem = @"OpenCodex 未能取得该账户的新额度；当前可用数值可能是缓存，请在 OpenCodex 中检查。";
        else if (!snapshot.primary && !snapshot.secondary) problem = @"OpenCodex 暂未返回该账户的额度窗口。";
        if (problem) account.refreshError = QuotaError(QuotaErrorAccountUnavailable, problem);
        [accounts addObject:account];
    }
    return accounts;
}

QuotaAccount *QuotaSelectedAccount(NSArray<QuotaAccount *> *accounts, NSString *selectedID) {
    for (QuotaAccount *account in accounts) {
        if (selectedID.length ? [account.accountID isEqualToString:selectedID] : account.active) return account;
    }
    // A removed saved account must never silently turn into a different monitored account.
    return selectedID.length ? nil : accounts.firstObject;
}

NSString *QuotaHistoryFileName(NSString *accountID) {
    NSData *data = [accountID dataUsingEncoding:NSUTF8StringEncoding];
    unsigned char digest[CC_SHA256_DIGEST_LENGTH];
    CC_SHA256(data.bytes, (CC_LONG)data.length, digest);
    NSMutableString *name = [NSMutableString stringWithString:@"account-"];
    for (NSUInteger index = 0; index < sizeof(digest); index++) [name appendFormat:@"%02x", digest[index]];
    return [name stringByAppendingString:@".csv"];
}

@interface OpenCodexQuotaService ()
@property(nonatomic, strong) dispatch_queue_t queue;
@property(nonatomic, strong, nullable) NSURL *explicitExecutableURL;
@property(nonatomic) NSTimeInterval timeout;
@property(nonatomic, strong, nullable) NSTask *task;
@property(nonatomic, strong) NSMutableData *output;
@property(nonatomic, copy, nullable) QuotaAccountsCompletion completion;
@property(nonatomic, copy, nullable) dispatch_block_t timeoutBlock;
@property(nonatomic) BOOL outputClosed;
@property(nonatomic) BOOL taskExited;
@end

@implementation OpenCodexQuotaService
- (instancetype)init { return [self initWithExecutableURL:nil timeout:60]; }

- (instancetype)initWithExecutableURL:(NSURL *)executableURL timeout:(NSTimeInterval)timeout {
    self = [super init];
    if (self) {
        _queue = dispatch_queue_create("app.codexquotabar.opencodex", DISPATCH_QUEUE_SERIAL);
        _explicitExecutableURL = executableURL;
        _timeout = timeout;
        _output = [NSMutableData data];
    }
    return self;
}

- (NSArray<NSString *> *)executableDirectories {
    return @[@"/opt/homebrew/bin", @"/usr/local/bin",
             [NSHomeDirectory() stringByAppendingPathComponent:@".local/bin"],
             [NSHomeDirectory() stringByAppendingPathComponent:@".bun/bin"],
             [NSHomeDirectory() stringByAppendingPathComponent:@".volta/bin"],
             [NSHomeDirectory() stringByAppendingPathComponent:@".asdf/shims"],
             [NSHomeDirectory() stringByAppendingPathComponent:@".local/share/mise/shims"]];
}

- (NSURL *)executableURL {
    if (self.explicitExecutableURL) return self.explicitExecutableURL;
    NSMutableOrderedSet<NSString *> *directories = [NSMutableOrderedSet orderedSetWithArray:self.executableDirectories];
    NSString *path = NSProcessInfo.processInfo.environment[@"PATH"] ?: @"";
    [directories addObjectsFromArray:[path componentsSeparatedByString:@":"]];
    for (NSString *directory in directories) {
        if (![directory hasPrefix:@"/"]) continue;
        for (NSString *name in @[@"ocx", @"opencodex"]) {
            NSString *candidate = [directory stringByAppendingPathComponent:name];
            if ([NSFileManager.defaultManager isExecutableFileAtPath:candidate]) return [NSURL fileURLWithPath:candidate];
        }
    }
    return nil;
}

- (NSDictionary<NSString *, NSString *> *)environmentForExecutableURL:(NSURL *)url {
    NSMutableDictionary *environment = [NSProcessInfo.processInfo.environment mutableCopy];
    NSMutableOrderedSet *directories = [NSMutableOrderedSet orderedSetWithObject:url.URLByDeletingLastPathComponent.path];
    [directories addObjectsFromArray:self.executableDirectories];
    [directories addObjectsFromArray:@[@"/usr/bin", @"/bin", @"/usr/sbin", @"/sbin"]];
    [directories addObjectsFromArray:[(environment[@"PATH"] ?: @"") componentsSeparatedByString:@":"]];
    [directories removeObject:@""];
    environment[@"PATH"] = [directories.array componentsJoinedByString:@":"];
    return environment;
}

- (void)fetch:(QuotaAccountsCompletion)completion {
    dispatch_async(self.queue, ^{
        if (self.completion) {
            dispatch_async(dispatch_get_main_queue(), ^{ completion(nil, QuotaError(QuotaErrorAlreadyRefreshing, @"正在读取 OpenCodex 额度。")); });
            return;
        }
        self.completion = completion;
        NSURL *url = [self executableURL];
        if (!url || ![NSFileManager.defaultManager isExecutableFileAtPath:url.path]) {
            [self finishWithAccounts:nil error:QuotaError(QuotaErrorCLIUnavailable, @"找不到 OpenCodex CLI（ocx）。请安装 OpenCodex，并确认 ocx status 正常。")];
            return;
        }
        [self.output setLength:0];
        self.outputClosed = NO;
        self.taskExited = NO;
        NSTask *task = [NSTask new];
        NSPipe *pipe = [NSPipe pipe];
        task.executableURL = url;
        task.arguments = @[@"account", @"list", @"openai", @"--quota", @"--refresh", @"--json"];
        task.environment = [self environmentForExecutableURL:url];
        task.standardInput = NSFileHandle.fileHandleWithNullDevice;
        task.standardOutput = pipe;
        // Never surface arbitrary CLI stderr (which can contain account or credential details).
        task.standardError = NSFileHandle.fileHandleWithNullDevice;
        self.task = task;
        __weak typeof(self) weakSelf = self;
        dispatch_queue_t queue = self.queue;
        pipe.fileHandleForReading.readabilityHandler = ^(NSFileHandle *handle) {
            NSData *data = handle.availableData;
            if (!data.length) handle.readabilityHandler = nil;
            dispatch_async(queue, ^{
                typeof(self) self = weakSelf;
                if (!self || self.task != task) return;
                if (data.length == 0) {
                    self.outputClosed = YES;
                    handle.readabilityHandler = nil;
                    [self completeIfReady];
                } else if (self.output.length + data.length > 2 * 1024 * 1024) {
                    [self finishWithAccounts:nil error:QuotaError(QuotaErrorProtocol, @"OpenCodex 返回的数据过大，已停止本次读取。")];
                } else {
                    [self.output appendData:data];
                }
            });
        };
        task.terminationHandler = ^(NSTask *finished) {
            dispatch_async(queue, ^{
                typeof(self) self = weakSelf;
                if (!self || self.task != finished) return;
                self.taskExited = YES;
                [self completeIfReady];
            });
        };
        if (![task launchAndReturnError:nil]) {
            [self finishWithAccounts:nil error:QuotaError(QuotaErrorLaunchFailed, @"无法启动 OpenCodex CLI，请确认 ocx --version 可以正常执行。")];
            return;
        }
        self.timeoutBlock = dispatch_block_create(0, ^{
            typeof(self) self = weakSelf;
            if (self.task == task) [self finishWithAccounts:nil error:QuotaError(QuotaErrorTimedOut, @"OpenCodex 额度读取超时，请确认服务运行正常并稍后刷新。")];
        });
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(self.timeout * NSEC_PER_SEC)), self.queue, self.timeoutBlock);
    });
}

- (void)completeIfReady {
    if (!self.taskExited || !self.outputClosed) return;
    if (self.task.terminationStatus != 0) {
        [self finishWithAccounts:nil error:QuotaError(QuotaErrorProtocol, @"OpenCodex 查询失败，请运行 ocx status 和 ocx account list openai --quota --refresh --json 检查服务与登录状态。")];
        return;
    }
    NSError *error = nil;
    NSArray *accounts = QuotaParseAccounts(self.output, &error);
    [self finishWithAccounts:accounts error:error];
}

- (void)finishWithAccounts:(NSArray<QuotaAccount *> *)accounts error:(NSError *)error {
    if (self.timeoutBlock) dispatch_block_cancel(self.timeoutBlock);
    self.timeoutBlock = nil;
    NSTask *task = self.task;
    self.task = nil;
    NSPipe *pipe = [task.standardOutput isKindOfClass:NSPipe.class] ? task.standardOutput : nil;
    pipe.fileHandleForReading.readabilityHandler = nil;
    task.terminationHandler = nil;
    if (task.running) {
        [task terminate];
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, NSEC_PER_SEC), self.queue, ^{
            if (task.running) kill(task.processIdentifier, SIGKILL);
        });
    }
    [self.output setLength:0];
    QuotaAccountsCompletion callback = self.completion;
    self.completion = nil;
    if (callback && (accounts || error)) dispatch_async(dispatch_get_main_queue(), ^{ callback(accounts, error); });
}

- (void)cancel {
    dispatch_async(self.queue, ^{ [self finishWithAccounts:nil error:nil]; });
}
@end
