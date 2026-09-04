#import <Cocoa/Cocoa.h>

static NSString *const QuotaErrorDomain = @"app.codexquotabar.desktop";
static NSString *const QuotaHistoryHeader = @"recorded_at,primary_used_percent,primary_remaining_percent,primary_window_minutes,primary_resets_at,secondary_used_percent,secondary_remaining_percent,secondary_window_minutes,secondary_resets_at\n";

typedef NS_ENUM(NSInteger, QuotaErrorCode) {
    QuotaErrorCodexNotFound = 1,
    QuotaErrorAlreadyRefreshing,
    QuotaErrorLaunchFailed,
    QuotaErrorProtocol,
    QuotaErrorTimedOut,
};

static NSError *QuotaError(QuotaErrorCode code, NSString *description) {
    return [NSError errorWithDomain:QuotaErrorDomain
                               code:code
                           userInfo:@{NSLocalizedDescriptionKey: description}];
}

@interface QuotaWindow : NSObject
@property(nonatomic) NSInteger usedPercent;
@property(nonatomic) NSInteger durationMinutes;
@property(nonatomic, strong) NSDate *resetsAt;
@property(nonatomic, readonly) NSInteger remainingPercent;
@end

@implementation QuotaWindow
- (NSInteger)remainingPercent {
    return MAX(0, MIN(100, 100 - self.usedPercent));
}
@end

@interface QuotaSnapshot : NSObject
@property(nonatomic, strong, nullable) QuotaWindow *primary;
@property(nonatomic, strong, nullable) QuotaWindow *secondary;
@property(nonatomic, copy, nullable) NSString *planType;
@property(nonatomic, copy, nullable) NSString *creditBalance;
@property(nonatomic, strong, nullable) NSNumber *resetCreditCount;
@property(nonatomic, strong) NSDate *updatedAt;
@end

@implementation QuotaSnapshot
@end

@interface QuotaHistoryPoint : NSObject
@property(nonatomic, strong) NSDate *recordedAt;
@property(nonatomic, strong, nullable) NSNumber *primaryRemainingPercent;
@property(nonatomic, strong, nullable) NSNumber *secondaryRemainingPercent;
@end

@implementation QuotaHistoryPoint
@end

@interface QuotaTrendView : NSView
@property(nonatomic, copy) NSArray<QuotaHistoryPoint *> *points;
@property(nonatomic) NSInteger totalRecordCount;
@property(nonatomic, strong) NSDateFormatter *axisDateFormatter;
- (instancetype)initWithPoints:(NSArray<QuotaHistoryPoint *> *)points
               totalRecordCount:(NSInteger)totalRecordCount;
@end

@implementation QuotaTrendView

- (instancetype)initWithPoints:(NSArray<QuotaHistoryPoint *> *)points
               totalRecordCount:(NSInteger)totalRecordCount {
    self = [super initWithFrame:NSMakeRect(0, 0, 340, 172)];
    if (self) {
        _points = [points copy];
        _totalRecordCount = totalRecordCount;
        _axisDateFormatter = [NSDateFormatter new];
        _axisDateFormatter.locale = [NSLocale localeWithLocaleIdentifier:@"zh_CN"];
        _axisDateFormatter.timeZone = NSTimeZone.localTimeZone;
        _axisDateFormatter.dateFormat = @"M/d HH:mm";
    }
    return self;
}

- (BOOL)isFlipped {
    return YES;
}

- (void)drawRect:(NSRect)dirtyRect {
    [super drawRect:dirtyRect];

    NSDictionary *titleAttributes = @{
        NSFontAttributeName: [NSFont systemFontOfSize:13 weight:NSFontWeightSemibold],
        NSForegroundColorAttributeName: NSColor.labelColor
    };
    NSDictionary *secondaryAttributes = @{
        NSFontAttributeName: [NSFont systemFontOfSize:9],
        NSForegroundColorAttributeName: NSColor.secondaryLabelColor
    };

    [@"使用趋势 · 剩余额度" drawAtPoint:NSMakePoint(14, 8) withAttributes:titleAttributes];
    NSString *countText = [NSString stringWithFormat:@"%ld 条记录", (long)self.totalRecordCount];
    NSSize countSize = [countText sizeWithAttributes:secondaryAttributes];
    [countText drawAtPoint:NSMakePoint(NSWidth(self.bounds) - countSize.width - 14, 11)
            withAttributes:secondaryAttributes];

    QuotaHistoryPoint *latest = self.points.lastObject;
    NSString *primaryText = latest.primaryRemainingPercent
        ? [NSString stringWithFormat:@"5 小时 %@%%", latest.primaryRemainingPercent]
        : @"5 小时 —";
    NSString *secondaryText = latest.secondaryRemainingPercent
        ? [NSString stringWithFormat:@"7 天 %@%%", latest.secondaryRemainingPercent]
        : @"7 天 —";
    CGFloat legendX = [self drawLegendAtX:14 y:31 color:NSColor.systemBlueColor text:primaryText];
    [self drawLegendAtX:legendX + 18 y:31 color:NSColor.systemPurpleColor text:secondaryText];

    NSRect chartRect = NSMakeRect(38, 57, NSWidth(self.bounds) - 52, 82);
    [self drawGridInRect:chartRect labelAttributes:secondaryAttributes];

    if (self.points.count == 0) {
        [self drawCenteredText:@"等待首次额度记录" inRect:chartRect attributes:secondaryAttributes];
        return;
    }

    NSDate *firstDate = self.points.firstObject.recordedAt;
    NSDate *lastDate = self.points.lastObject.recordedAt;
    [self drawSeriesPrimary:YES color:NSColor.systemBlueColor inRect:chartRect firstDate:firstDate lastDate:lastDate];
    [self drawSeriesPrimary:NO color:NSColor.systemPurpleColor inRect:chartRect firstDate:firstDate lastDate:lastDate];

    if (self.points.count == 1) {
        [self drawCenteredText:@"已建立起点，额度变化后形成趋势线"
                       inRect:NSMakeRect(NSMinX(chartRect), NSMidY(chartRect) - 7, NSWidth(chartRect), 14)
                   attributes:secondaryAttributes];
        NSString *dateText = [self.axisDateFormatter stringFromDate:firstDate];
        NSSize dateSize = [dateText sizeWithAttributes:secondaryAttributes];
        [dateText drawAtPoint:NSMakePoint(NSMidX(chartRect) - dateSize.width / 2, NSMaxY(chartRect) + 7)
               withAttributes:secondaryAttributes];
    } else {
        NSString *firstText = [self.axisDateFormatter stringFromDate:firstDate];
        NSString *lastText = [self.axisDateFormatter stringFromDate:lastDate];
        [firstText drawAtPoint:NSMakePoint(NSMinX(chartRect), NSMaxY(chartRect) + 7)
                withAttributes:secondaryAttributes];
        NSSize lastSize = [lastText sizeWithAttributes:secondaryAttributes];
        [lastText drawAtPoint:NSMakePoint(NSMaxX(chartRect) - lastSize.width, NSMaxY(chartRect) + 7)
               withAttributes:secondaryAttributes];
    }
}

- (CGFloat)drawLegendAtX:(CGFloat)x y:(CGFloat)y color:(NSColor *)color text:(NSString *)text {
    [color setFill];
    [[NSBezierPath bezierPathWithOvalInRect:NSMakeRect(x, y + 3, 7, 7)] fill];
    NSDictionary *attributes = @{
        NSFontAttributeName: [NSFont monospacedDigitSystemFontOfSize:11 weight:NSFontWeightMedium],
        NSForegroundColorAttributeName: NSColor.labelColor
    };
    [text drawAtPoint:NSMakePoint(x + 11, y) withAttributes:attributes];
    return x + 11 + [text sizeWithAttributes:attributes].width;
}

- (void)drawGridInRect:(NSRect)chartRect labelAttributes:(NSDictionary *)labelAttributes {
    for (NSNumber *level in @[@100, @50, @0]) {
        CGFloat y = NSMinY(chartRect) + (100.0 - level.doubleValue) / 100.0 * NSHeight(chartRect);
        NSString *label = [NSString stringWithFormat:@"%@", level];
        NSSize size = [label sizeWithAttributes:labelAttributes];
        [label drawAtPoint:NSMakePoint(NSMinX(chartRect) - size.width - 6, y - size.height / 2)
            withAttributes:labelAttributes];

        NSBezierPath *gridLine = [NSBezierPath bezierPath];
        [gridLine moveToPoint:NSMakePoint(NSMinX(chartRect), y)];
        [gridLine lineToPoint:NSMakePoint(NSMaxX(chartRect), y)];
        gridLine.lineWidth = 0.5;
        [[NSColor.separatorColor colorWithAlphaComponent:0.55] setStroke];
        [gridLine stroke];
    }
}

- (void)drawSeriesPrimary:(BOOL)primary
                    color:(NSColor *)color
                   inRect:(NSRect)chartRect
                firstDate:(NSDate *)firstDate
                 lastDate:(NSDate *)lastDate {
    NSTimeInterval span = [lastDate timeIntervalSinceDate:firstDate];
    NSMutableArray<NSValue *> *displayPoints = [NSMutableArray array];

    for (QuotaHistoryPoint *point in self.points) {
        NSNumber *value = primary ? point.primaryRemainingPercent : point.secondaryRemainingPercent;
        if (!value) continue;
        CGFloat x = span > 0
            ? NSMinX(chartRect) + [point.recordedAt timeIntervalSinceDate:firstDate] / span * NSWidth(chartRect)
            : NSMidX(chartRect);
        CGFloat clampedValue = MAX(0.0, MIN(100.0, value.doubleValue));
        CGFloat y = NSMinY(chartRect) + (100.0 - clampedValue) / 100.0 * NSHeight(chartRect);
        [displayPoints addObject:[NSValue valueWithPoint:NSMakePoint(x, y)]];
    }

    if (displayPoints.count == 0) return;
    NSBezierPath *line = [NSBezierPath bezierPath];
    line.lineWidth = 2.0;
    line.lineCapStyle = NSLineCapStyleRound;
    line.lineJoinStyle = NSLineJoinStyleRound;
    [line moveToPoint:displayPoints.firstObject.pointValue];
    for (NSUInteger index = 1; index < displayPoints.count; index++) {
        [line lineToPoint:displayPoints[index].pointValue];
    }
    [color setStroke];
    [line stroke];

    for (NSUInteger index = 0; index < displayPoints.count; index++) {
        if (displayPoints.count > 12 && index + 1 != displayPoints.count) continue;
        NSPoint point = displayPoints[index].pointValue;
        [color setFill];
        [[NSBezierPath bezierPathWithOvalInRect:NSMakeRect(point.x - 2.5, point.y - 2.5, 5, 5)] fill];
    }
}

- (void)drawCenteredText:(NSString *)text
                   inRect:(NSRect)rect
               attributes:(NSDictionary *)attributes {
    NSSize size = [text sizeWithAttributes:attributes];
    [text drawAtPoint:NSMakePoint(NSMidX(rect) - size.width / 2, NSMidY(rect) - size.height / 2)
        withAttributes:attributes];
}

@end

typedef void (^QuotaCompletion)(QuotaSnapshot *_Nullable snapshot, NSError *_Nullable error);

@interface CodexQuotaService : NSObject
@property(nonatomic) dispatch_queue_t queue;
@property(nonatomic, strong, nullable) NSTask *task;
@property(nonatomic, strong) NSMutableData *outputBuffer;
@property(nonatomic, copy, nullable) QuotaCompletion completion;
@property(nonatomic, copy, nullable) dispatch_block_t timeoutBlock;
@property(nonatomic) BOOL refreshing;
- (void)fetch:(QuotaCompletion)completion;
- (void)cancel;
- (nullable NSURL *)codexExecutableURL;
- (NSDictionary<NSString *, NSString *> *)launchEnvironmentForExecutableURL:(NSURL *)executableURL;
@end

@implementation CodexQuotaService

- (instancetype)init {
    self = [super init];
    if (self) {
        _queue = dispatch_queue_create("app.codexquotabar.desktop.service", DISPATCH_QUEUE_SERIAL);
        _outputBuffer = [NSMutableData data];
    }
    return self;
}

- (void)fetch:(QuotaCompletion)completion {
    __weak typeof(self) weakSelf = self;
    dispatch_async(self.queue, ^{
        typeof(self) self = weakSelf;
        if (!self) return;

        if (self.refreshing) {
            dispatch_async(dispatch_get_main_queue(), ^{
                completion(nil, QuotaError(QuotaErrorAlreadyRefreshing, @"额度正在刷新。"));
            });
            return;
        }

        NSURL *executableURL = [self codexExecutableURL];
        if (!executableURL) {
            dispatch_async(dispatch_get_main_queue(), ^{
                completion(nil, QuotaError(QuotaErrorCodexNotFound, @"找不到 Codex CLI。请先安装或更新 Codex。"));
            });
            return;
        }

        self.refreshing = YES;
        self.completion = completion;
        [self.outputBuffer setLength:0];

        NSTask *task = [[NSTask alloc] init];
        NSPipe *inputPipe = [NSPipe pipe];
        NSPipe *outputPipe = [NSPipe pipe];
        NSPipe *errorPipe = [NSPipe pipe];

        task.executableURL = executableURL;
        task.arguments = @[@"app-server"];
        task.environment = [self launchEnvironmentForExecutableURL:executableURL];
        task.standardInput = inputPipe;
        task.standardOutput = outputPipe;
        task.standardError = errorPipe;
        self.task = task;

        outputPipe.fileHandleForReading.readabilityHandler = ^(NSFileHandle *handle) {
            NSData *data = handle.availableData;
            if (data.length == 0) return;
            dispatch_async(weakSelf.queue, ^{
                [weakSelf consumeData:data];
            });
        };

        task.terminationHandler = ^(NSTask *terminatedTask) {
            dispatch_async(weakSelf.queue, ^{
                typeof(self) self = weakSelf;
                if (!self || !self.refreshing) return;
                NSData *errorData = [errorPipe.fileHandleForReading readDataToEndOfFile];
                NSString *message = [[NSString alloc] initWithData:errorData encoding:NSUTF8StringEncoding];
                message = [message stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
                if (message.length == 0) {
                    message = [NSString stringWithFormat:@"进程已退出（状态 %d）", terminatedTask.terminationStatus];
                }
                [self finishWithSnapshot:nil error:QuotaError(QuotaErrorProtocol, [@"Codex 返回异常：" stringByAppendingString:message])];
            });
        };

        NSError *launchError = nil;
        if (![task launchAndReturnError:&launchError]) {
            NSString *message = [@"无法启动 Codex：" stringByAppendingString:launchError.localizedDescription ?: @"未知错误"];
            [self finishWithSnapshot:nil error:QuotaError(QuotaErrorLaunchFailed, message)];
            return;
        }

        NSString *clientVersion = [NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleShortVersionString"];
        if (![clientVersion isKindOfClass:NSString.class] || clientVersion.length == 0) {
            clientVersion = @"unknown";
        }
        NSDictionary *initialize = @{
            @"method": @"initialize",
            @"id": @0,
            @"params": @{
                @"clientInfo": @{
                    @"name": @"codex_quota_bar",
                    @"title": @"Codex Quota Bar",
                    @"version": clientVersion
                }
            }
        };
        [self sendObject:initialize toHandle:inputPipe.fileHandleForWriting];

        dispatch_block_t timeout = dispatch_block_create(0, ^{
            typeof(self) self = weakSelf;
            if (!self || !self.refreshing) return;
            [self finishWithSnapshot:nil error:QuotaError(QuotaErrorTimedOut, @"读取超时，请确认 Codex 已登录。")];
        });
        self.timeoutBlock = timeout;
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 15 * NSEC_PER_SEC), self.queue, timeout);
    });
}

- (void)cancel {
    __weak typeof(self) weakSelf = self;
    dispatch_async(self.queue, ^{
        [weakSelf finishWithSnapshot:nil error:nil];
    });
}

- (nullable NSURL *)codexExecutableURL {
    NSMutableArray<NSString *> *candidates = [@[
        @"/opt/homebrew/bin/codex",
        @"/usr/local/bin/codex",
        @"/Applications/Codex.app/Contents/Resources/codex",
        @"/Applications/Codex.app/Contents/Resources/bin/codex"
    ] mutableCopy];
    [candidates addObject:[NSHomeDirectory() stringByAppendingPathComponent:@".local/bin/codex"]];

    for (NSString *path in candidates) {
        if ([NSFileManager.defaultManager isExecutableFileAtPath:path]) {
            return [NSURL fileURLWithPath:path];
        }
    }
    return nil;
}

- (NSDictionary<NSString *, NSString *> *)launchEnvironmentForExecutableURL:(NSURL *)executableURL {
    NSMutableDictionary<NSString *, NSString *> *environment = [NSProcessInfo.processInfo.environment mutableCopy];
    NSMutableOrderedSet<NSString *> *pathEntries = [NSMutableOrderedSet orderedSet];
    NSString *home = NSHomeDirectory();
    NSArray<NSString *> *preferredEntries = @[
        executableURL.URLByDeletingLastPathComponent.path ?: @"",
        @"/opt/homebrew/bin",
        @"/usr/local/bin",
        [home stringByAppendingPathComponent:@".local/bin"],
        [home stringByAppendingPathComponent:@".volta/bin"],
        [home stringByAppendingPathComponent:@".asdf/shims"],
        [home stringByAppendingPathComponent:@".local/share/mise/shims"],
        @"/usr/bin",
        @"/bin",
        @"/usr/sbin",
        @"/sbin"
    ];

    for (NSString *entry in preferredEntries) {
        if (entry.length > 0) [pathEntries addObject:entry];
    }

    NSString *inheritedPath = environment[@"PATH"];
    for (NSString *entry in [inheritedPath componentsSeparatedByString:@":"]) {
        if (entry.length > 0) [pathEntries addObject:entry];
    }

    environment[@"PATH"] = [pathEntries.array componentsJoinedByString:@":"];
    return environment;
}

- (void)consumeData:(NSData *)data {
    [self.outputBuffer appendData:data];
    const uint8_t newline = '\n';

    while (self.outputBuffer.length > 0) {
        NSRange newlineRange = [self.outputBuffer rangeOfData:[NSData dataWithBytes:&newline length:1]
                                                      options:0
                                                        range:NSMakeRange(0, self.outputBuffer.length)];
        if (newlineRange.location == NSNotFound) break;

        NSData *lineData = [self.outputBuffer subdataWithRange:NSMakeRange(0, newlineRange.location)];
        [self.outputBuffer replaceBytesInRange:NSMakeRange(0, NSMaxRange(newlineRange)) withBytes:NULL length:0];
        if (lineData.length > 0) [self processLine:lineData];
    }
}

- (void)processLine:(NSData *)data {
    NSError *jsonError = nil;
    id object = [NSJSONSerialization JSONObjectWithData:data options:0 error:&jsonError];
    if (![object isKindOfClass:NSDictionary.class]) return;

    NSDictionary *message = object;
    NSNumber *identifier = [message[@"id"] isKindOfClass:NSNumber.class] ? message[@"id"] : nil;

    if (identifier.integerValue == 0 && message[@"result"]) {
        NSPipe *inputPipe = [self.task.standardInput isKindOfClass:NSPipe.class] ? self.task.standardInput : nil;
        if (!inputPipe) {
            [self finishWithSnapshot:nil error:QuotaError(QuotaErrorProtocol, @"Codex 返回异常：初始化通道不可用")];
            return;
        }
        [self sendObject:@{@"method": @"initialized", @"params": @{}}
                toHandle:inputPipe.fileHandleForWriting];
        [self sendObject:@{@"method": @"account/rateLimits/read", @"id": @1}
                toHandle:inputPipe.fileHandleForWriting];
        return;
    }

    if (identifier.integerValue != 1) return;

    NSDictionary *protocolError = [message[@"error"] isKindOfClass:NSDictionary.class] ? message[@"error"] : nil;
    if (protocolError) {
        NSString *detail = [protocolError[@"message"] isKindOfClass:NSString.class] ? protocolError[@"message"] : @"未知协议错误";
        [self finishWithSnapshot:nil error:QuotaError(QuotaErrorProtocol, [@"Codex 返回异常：" stringByAppendingString:detail])];
        return;
    }

    NSDictionary *result = [message[@"result"] isKindOfClass:NSDictionary.class] ? message[@"result"] : nil;
    QuotaSnapshot *snapshot = [self parseSnapshot:result];
    if (!snapshot) {
        [self finishWithSnapshot:nil error:QuotaError(QuotaErrorProtocol, @"Codex 返回异常：缺少可识别的额度窗口")];
        return;
    }

    [self finishWithSnapshot:snapshot error:nil];
}

- (nullable QuotaSnapshot *)parseSnapshot:(nullable NSDictionary *)result {
    if (!result) return nil;
    NSDictionary *legacy = [result[@"rateLimits"] isKindOfClass:NSDictionary.class] ? result[@"rateLimits"] : nil;
    NSDictionary *byLimitId = [result[@"rateLimitsByLimitId"] isKindOfClass:NSDictionary.class] ? result[@"rateLimitsByLimitId"] : nil;
    NSDictionary *codexBucket = [byLimitId[@"codex"] isKindOfClass:NSDictionary.class] ? byLimitId[@"codex"] : nil;
    NSDictionary *bucket = codexBucket ?: legacy;
    if (!bucket) return nil;

    QuotaWindow *primary = [self parseWindow:bucket[@"primary"]];
    QuotaWindow *secondary = [self parseWindow:bucket[@"secondary"]];
    if (!primary && !secondary) return nil;

    NSDictionary *credits = [bucket[@"credits"] isKindOfClass:NSDictionary.class] ? bucket[@"credits"] : nil;
    NSDictionary *resetCredits = [result[@"rateLimitResetCredits"] isKindOfClass:NSDictionary.class] ? result[@"rateLimitResetCredits"] : nil;

    QuotaSnapshot *snapshot = [QuotaSnapshot new];
    snapshot.primary = primary;
    snapshot.secondary = secondary;
    snapshot.planType = [bucket[@"planType"] isKindOfClass:NSString.class] ? bucket[@"planType"] : nil;
    snapshot.creditBalance = [credits[@"balance"] isKindOfClass:NSString.class] ? credits[@"balance"] : nil;
    snapshot.resetCreditCount = [resetCredits[@"availableCount"] isKindOfClass:NSNumber.class] ? resetCredits[@"availableCount"] : nil;
    snapshot.updatedAt = [NSDate date];
    return snapshot;
}

- (nullable QuotaWindow *)parseWindow:(id)value {
    if (![value isKindOfClass:NSDictionary.class]) return nil;
    NSDictionary *dictionary = value;
    NSNumber *used = [dictionary[@"usedPercent"] isKindOfClass:NSNumber.class] ? dictionary[@"usedPercent"] : nil;
    NSNumber *duration = [dictionary[@"windowDurationMins"] isKindOfClass:NSNumber.class] ? dictionary[@"windowDurationMins"] : nil;
    NSNumber *resetTimestamp = [dictionary[@"resetsAt"] isKindOfClass:NSNumber.class] ? dictionary[@"resetsAt"] : nil;
    if (!used || !duration || !resetTimestamp) return nil;

    QuotaWindow *window = [QuotaWindow new];
    window.usedPercent = MAX(0, MIN(100, used.integerValue));
    window.durationMinutes = duration.integerValue;
    window.resetsAt = [NSDate dateWithTimeIntervalSince1970:resetTimestamp.doubleValue];
    return window;
}

- (void)sendObject:(NSDictionary *)object toHandle:(NSFileHandle *)handle {
    NSError *error = nil;
    NSData *json = [NSJSONSerialization dataWithJSONObject:object options:0 error:&error];
    if (!json || error) {
        [self finishWithSnapshot:nil error:QuotaError(QuotaErrorProtocol, @"Codex 返回异常：无法编码请求")];
        return;
    }
    NSMutableData *line = [json mutableCopy];
    const uint8_t newline = '\n';
    [line appendBytes:&newline length:1];
    [handle writeData:line];
}

- (void)finishWithSnapshot:(nullable QuotaSnapshot *)snapshot error:(nullable NSError *)error {
    if (!self.refreshing) return;
    self.refreshing = NO;

    if (self.timeoutBlock) {
        dispatch_block_cancel(self.timeoutBlock);
        self.timeoutBlock = nil;
    }

    NSPipe *outputPipe = [self.task.standardOutput isKindOfClass:NSPipe.class] ? self.task.standardOutput : nil;
    outputPipe.fileHandleForReading.readabilityHandler = nil;
    self.task.terminationHandler = nil;

    NSPipe *inputPipe = [self.task.standardInput isKindOfClass:NSPipe.class] ? self.task.standardInput : nil;
    [inputPipe.fileHandleForWriting closeFile];
    if (self.task.running) [self.task terminate];
    self.task = nil;

    QuotaCompletion callback = self.completion;
    self.completion = nil;
    if (!callback || (!snapshot && !error)) return;

    dispatch_async(dispatch_get_main_queue(), ^{
        callback(snapshot, error);
    });
}

@end

@interface AppDelegate : NSObject <NSApplicationDelegate, NSMenuDelegate>
@property(nonatomic, strong) CodexQuotaService *service;
@property(nonatomic, strong) NSStatusItem *statusItem;
@property(nonatomic, strong, nullable) NSTimer *timer;
@property(nonatomic, strong, nullable) QuotaSnapshot *snapshot;
@property(nonatomic, strong, nullable) NSError *lastError;
@property(nonatomic) BOOL loading;
@property(nonatomic) NSInteger unchangedRefreshCount;
@property(nonatomic) NSInteger consecutiveFailures;
@property(nonatomic, strong, nullable) NSDate *lastRefreshCompletedAt;
@property(nonatomic, strong) NSDateFormatter *dateFormatter;
@property(nonatomic, strong) NSISO8601DateFormatter *historyDateFormatter;
@property(nonatomic, strong, nullable) NSURL *historyFileURL;
@property(nonatomic, copy, nullable) NSString *lastHistorySignature;
@property(nonatomic) NSInteger historyRecordCount;
@property(nonatomic, strong) NSMutableArray<QuotaHistoryPoint *> *historyPoints;
@end

@implementation AppDelegate

- (instancetype)init {
    self = [super init];
    if (self) {
        _service = [CodexQuotaService new];
        _dateFormatter = [NSDateFormatter new];
        _dateFormatter.locale = [NSLocale localeWithLocaleIdentifier:@"zh_CN"];
        _dateFormatter.timeZone = NSTimeZone.localTimeZone;
        _dateFormatter.dateFormat = @"M月d日 HH:mm";
        _historyDateFormatter = [NSISO8601DateFormatter new];
        _historyDateFormatter.timeZone = NSTimeZone.localTimeZone;
        _historyDateFormatter.formatOptions = NSISO8601DateFormatWithInternetDateTime |
                                              NSISO8601DateFormatWithFractionalSeconds;
        _historyPoints = [NSMutableArray array];
    }
    return self;
}

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    [NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
    [self prepareUsageHistory];
    [self configureStatusItem];

    [NSNotificationCenter.defaultCenter addObserver:self
                                           selector:@selector(powerStateDidChange:)
                                               name:NSProcessInfoPowerStateDidChangeNotification
                                             object:nil];
    [NSWorkspace.sharedWorkspace.notificationCenter addObserver:self
                                                       selector:@selector(workspaceDidWake:)
                                                           name:NSWorkspaceDidWakeNotification
                                                         object:nil];
    [self refresh];
}

- (void)applicationWillTerminate:(NSNotification *)notification {
    [self.timer invalidate];
    [NSNotificationCenter.defaultCenter removeObserver:self];
    [NSWorkspace.sharedWorkspace.notificationCenter removeObserver:self];
    [self.service cancel];
}

- (void)menuWillOpen:(NSMenu *)menu {
    [self rebuildMenu];

    BOOL stale = !self.lastRefreshCompletedAt ||
        -[self.lastRefreshCompletedAt timeIntervalSinceNow] > 20;
    if (stale && !self.loading) {
        __weak typeof(self) weakSelf = self;
        dispatch_async(dispatch_get_main_queue(), ^{
            [weakSelf refresh];
        });
    }
}

- (void)configureStatusItem {
    self.statusItem = [NSStatusBar.systemStatusBar statusItemWithLength:NSVariableStatusItemLength];
    NSStatusBarButton *button = self.statusItem.button;
    button.image = [NSImage imageWithSystemSymbolName:@"gauge.with.dots.needle.50percent"
                           accessibilityDescription:@"Codex 额度"];
    button.image.template = YES;
    button.imagePosition = NSImageLeading;
    button.font = [NSFont monospacedDigitSystemFontOfSize:NSFont.systemFontSize weight:NSFontWeightMedium];
    button.title = @"…";
    button.toolTip = @"正在读取 Codex 额度";

    NSMenu *menu = [NSMenu new];
    menu.delegate = self;
    self.statusItem.menu = menu;
    [self rebuildMenu];
}

- (void)refresh {
    if (self.loading) return;
    [self.timer invalidate];
    self.timer = nil;
    self.loading = YES;
    [self updateStatusDisplay];
    [self rebuildMenu];

    __weak typeof(self) weakSelf = self;
    [self.service fetch:^(QuotaSnapshot *snapshot, NSError *error) {
        typeof(self) self = weakSelf;
        if (!self) return;
        self.loading = NO;
        NSTimeInterval nextInterval = 60;

        if (snapshot) {
            BOOL changed = [self snapshot:snapshot differsFrom:self.snapshot];
            if (changed) {
                self.unchangedRefreshCount = 0;
            } else {
                self.unchangedRefreshCount += 1;
            }
            self.consecutiveFailures = 0;
            self.snapshot = snapshot;
            [self recordSnapshotIfChanged:snapshot];
            self.lastError = nil;
            self.lastRefreshCompletedAt = snapshot.updatedAt;
            nextInterval = [self nextSuccessfulRefreshIntervalChanged:changed];
            NSLog(@"CodexQuotaBar refreshed: primary=%ld%% remaining, secondary=%ld%% remaining",
                  (long)(snapshot.primary ? snapshot.primary.remainingPercent : -1),
                  (long)(snapshot.secondary ? snapshot.secondary.remainingPercent : -1));
        } else if (error.code != QuotaErrorAlreadyRefreshing) {
            self.consecutiveFailures += 1;
            self.lastError = error;
            nextInterval = [self nextFailureRefreshInterval];
            NSLog(@"CodexQuotaBar refresh failed: %@", error.localizedDescription);
        }

        [self updateStatusDisplay];
        [self rebuildMenu];
        [self scheduleNextRefreshAfter:nextInterval];
    }];
}

- (void)scheduledRefresh:(NSTimer *)timer {
    [self refresh];
}

- (void)scheduleNextRefreshAfter:(NSTimeInterval)interval {
    [self.timer invalidate];
    self.timer = [NSTimer scheduledTimerWithTimeInterval:interval
                                                 target:self
                                               selector:@selector(scheduledRefresh:)
                                               userInfo:nil
                                                repeats:NO];
    self.timer.tolerance = MIN(5.0, MAX(1.0, interval * 0.05));
    NSLog(@"CodexQuotaBar next refresh in %.0fs%@",
          interval,
          NSProcessInfo.processInfo.lowPowerModeEnabled ? @" (low power)" : @"");
}

- (NSTimeInterval)nextSuccessfulRefreshIntervalChanged:(BOOL)changed {
    if (NSProcessInfo.processInfo.lowPowerModeEnabled) return 300;
    if (changed || [self quotaIsNearThreshold:self.snapshot]) return 30;
    if (self.unchangedRefreshCount <= 4) return 60;
    return 120;
}

- (NSTimeInterval)nextFailureRefreshInterval {
    if (NSProcessInfo.processInfo.lowPowerModeEnabled) return 300;
    if (self.consecutiveFailures <= 1) return 60;
    if (self.consecutiveFailures == 2) return 120;
    return 300;
}

- (BOOL)quotaIsNearThreshold:(QuotaSnapshot *)snapshot {
    return (snapshot.primary && snapshot.primary.remainingPercent <= 20) ||
           (snapshot.secondary && snapshot.secondary.remainingPercent <= 20);
}

- (BOOL)snapshot:(QuotaSnapshot *)snapshot differsFrom:(nullable QuotaSnapshot *)previous {
    if (!previous) return YES;
    if ([self window:snapshot.primary differsFrom:previous.primary]) return YES;
    if ([self window:snapshot.secondary differsFrom:previous.secondary]) return YES;
    if (![self nullableString:snapshot.planType equals:previous.planType]) return YES;
    if (![self nullableString:snapshot.creditBalance equals:previous.creditBalance]) return YES;
    return ![snapshot.resetCreditCount isEqualToNumber:previous.resetCreditCount];
}

- (BOOL)window:(nullable QuotaWindow *)window differsFrom:(nullable QuotaWindow *)previous {
    if (!window || !previous) return window != previous;
    return window.usedPercent != previous.usedPercent ||
           window.durationMinutes != previous.durationMinutes ||
           fabs([window.resetsAt timeIntervalSinceDate:previous.resetsAt]) > 1;
}

- (BOOL)nullableString:(nullable NSString *)value equals:(nullable NSString *)other {
    return value == other || [value isEqualToString:other];
}

- (void)powerStateDidChange:(NSNotification *)notification {
    if (self.loading) return;
    if (NSProcessInfo.processInfo.lowPowerModeEnabled) {
        [self scheduleNextRefreshAfter:300];
    } else {
        [self refresh];
    }
}

- (void)workspaceDidWake:(NSNotification *)notification {
    if (!self.loading) [self refresh];
}

- (void)quit {
    [NSApp terminate:nil];
}

- (void)prepareUsageHistory {
    NSFileManager *fileManager = NSFileManager.defaultManager;
    NSError *error = nil;
    NSURL *applicationSupportURL = [fileManager URLForDirectory:NSApplicationSupportDirectory
                                                       inDomain:NSUserDomainMask
                                              appropriateForURL:nil
                                                         create:YES
                                                          error:&error];
    if (!applicationSupportURL) {
        NSLog(@"CodexQuotaBar could not locate Application Support: %@", error.localizedDescription);
        return;
    }

    NSURL *directoryURL = [applicationSupportURL URLByAppendingPathComponent:@"CodexQuotaBar" isDirectory:YES];
    if (![fileManager createDirectoryAtURL:directoryURL
               withIntermediateDirectories:YES
                                attributes:nil
                                     error:&error]) {
        NSLog(@"CodexQuotaBar could not create history directory: %@", error.localizedDescription);
        return;
    }

    NSURL *fileURL = [directoryURL URLByAppendingPathComponent:@"quota-history.csv" isDirectory:NO];
    if (![fileManager fileExistsAtPath:fileURL.path]) {
        if (![QuotaHistoryHeader writeToURL:fileURL atomically:YES encoding:NSUTF8StringEncoding error:&error]) {
            NSLog(@"CodexQuotaBar could not create history file: %@", error.localizedDescription);
            return;
        }
        [fileManager setAttributes:@{NSFilePosixPermissions: @0600} ofItemAtPath:fileURL.path error:nil];
    }

    NSString *contents = [NSString stringWithContentsOfURL:fileURL
                                                  encoding:NSUTF8StringEncoding
                                                     error:&error];
    if (!contents) {
        NSLog(@"CodexQuotaBar could not read history file: %@", error.localizedDescription);
        return;
    }

    self.historyFileURL = fileURL;
    self.historyRecordCount = 0;
    self.lastHistorySignature = nil;
    [self.historyPoints removeAllObjects];

    NSArray<NSString *> *lines = [contents componentsSeparatedByCharactersInSet:NSCharacterSet.newlineCharacterSet];
    for (NSUInteger index = 1; index < lines.count; index++) {
        NSString *line = lines[index];
        if (line.length == 0) continue;
        NSArray<NSString *> *columns = [line componentsSeparatedByString:@","];
        if (columns.count != 9) continue;
        NSString *signature = [[columns subarrayWithRange:NSMakeRange(1, 8)] componentsJoinedByString:@","];
        if ([signature isEqualToString:self.lastHistorySignature]) continue;

        NSDate *recordedAt = [self.historyDateFormatter dateFromString:columns[0]];
        if (recordedAt) {
            QuotaHistoryPoint *point = [QuotaHistoryPoint new];
            point.recordedAt = recordedAt;
            if (columns[2].length > 0) point.primaryRemainingPercent = @(columns[2].integerValue);
            if (columns[6].length > 0) point.secondaryRemainingPercent = @(columns[6].integerValue);
            [self.historyPoints addObject:point];
            if (self.historyPoints.count > 120) [self.historyPoints removeObjectAtIndex:0];
        }
        self.lastHistorySignature = signature;
        self.historyRecordCount += 1;
    }
}

- (NSArray<NSString *> *)historyFieldsForWindow:(nullable QuotaWindow *)window {
    if (!window) return @[@"", @"", @"", @""];
    return @[
        [NSString stringWithFormat:@"%ld", (long)window.usedPercent],
        [NSString stringWithFormat:@"%ld", (long)window.remainingPercent],
        [NSString stringWithFormat:@"%ld", (long)window.durationMinutes],
        [self.historyDateFormatter stringFromDate:window.resetsAt]
    ];
}

- (void)recordSnapshotIfChanged:(QuotaSnapshot *)snapshot {
    if (!self.historyFileURL) [self prepareUsageHistory];
    if (!self.historyFileURL) return;

    NSMutableArray<NSString *> *fields = [NSMutableArray array];
    [fields addObjectsFromArray:[self historyFieldsForWindow:snapshot.primary]];
    [fields addObjectsFromArray:[self historyFieldsForWindow:snapshot.secondary]];
    NSString *signature = [fields componentsJoinedByString:@","];
    if ([signature isEqualToString:self.lastHistorySignature]) return;

    // Another instance may have appended while this process was refreshing.
    // Reload immediately before a changed write so the same point is not duplicated.
    [self prepareUsageHistory];
    if (!self.historyFileURL || [signature isEqualToString:self.lastHistorySignature]) return;

    NSString *recordedAt = [self.historyDateFormatter stringFromDate:snapshot.updatedAt];
    NSString *line = [NSString stringWithFormat:@"%@,%@\n", recordedAt, signature];
    NSData *data = [line dataUsingEncoding:NSUTF8StringEncoding];
    NSError *error = nil;
    NSFileHandle *handle = [NSFileHandle fileHandleForWritingToURL:self.historyFileURL error:&error];
    if (!handle || ![handle seekToEndReturningOffset:nil error:&error] || ![handle writeData:data error:&error]) {
        NSLog(@"CodexQuotaBar could not append history: %@", error.localizedDescription);
        [handle closeAndReturnError:nil];
        return;
    }
    [handle closeAndReturnError:nil];

    self.lastHistorySignature = signature;
    self.historyRecordCount += 1;
    QuotaHistoryPoint *point = [QuotaHistoryPoint new];
    point.recordedAt = snapshot.updatedAt;
    if (snapshot.primary) point.primaryRemainingPercent = @(snapshot.primary.remainingPercent);
    if (snapshot.secondary) point.secondaryRemainingPercent = @(snapshot.secondary.remainingPercent);
    [self.historyPoints addObject:point];
    if (self.historyPoints.count > 120) [self.historyPoints removeObjectAtIndex:0];
}

- (void)updateStatusDisplay {
    NSStatusBarButton *button = self.statusItem.button;
    if (self.snapshot) {
        NSMutableArray<NSString *> *values = [NSMutableArray array];
        if (self.snapshot.primary) [values addObject:[NSString stringWithFormat:@"%ld%%", (long)self.snapshot.primary.remainingPercent]];
        if (self.snapshot.secondary) [values addObject:[NSString stringWithFormat:@"%ld%%", (long)self.snapshot.secondary.remainingPercent]];
        button.title = values.count ? [values componentsJoinedByString:@" · "] : @"—";
        button.toolTip = [self tooltipForSnapshot:self.snapshot];
        if (self.loading) button.toolTip = [button.toolTip stringByAppendingString:@"\n正在刷新…"];
    } else if (self.loading) {
        button.title = @"…";
        button.toolTip = @"正在读取 Codex 额度";
    } else {
        button.title = @"!";
        button.toolTip = self.lastError.localizedDescription ?: @"额度读取失败";
    }
}

- (void)rebuildMenu {
    NSMenu *menu = self.statusItem.menu;
    [menu removeAllItems];

    [self addDisabledItem:@"Codex 额度栏" toMenu:menu];
    [menu addItem:NSMenuItem.separatorItem];

    if (self.snapshot) {
        [self addWindow:self.snapshot.primary fallbackName:@"短窗口" toMenu:menu];
        if (self.snapshot.primary && self.snapshot.secondary) [menu addItem:NSMenuItem.separatorItem];
        [self addWindow:self.snapshot.secondary fallbackName:@"长窗口" toMenu:menu];

        if (self.snapshot.planType || self.snapshot.creditBalance || self.snapshot.resetCreditCount) {
            [menu addItem:NSMenuItem.separatorItem];
        }
        if (self.snapshot.planType) {
            [self addDisabledItem:[NSString stringWithFormat:@"套餐：%@", self.snapshot.planType.uppercaseString] toMenu:menu];
        }
        if (self.snapshot.creditBalance) {
            [self addDisabledItem:[NSString stringWithFormat:@"Credits：%@", [self formatBalance:self.snapshot.creditBalance]] toMenu:menu];
        }
        if (self.snapshot.resetCreditCount) {
            [self addDisabledItem:[NSString stringWithFormat:@"可用重置券：%@", self.snapshot.resetCreditCount] toMenu:menu];
        }
        [self addDisabledItem:[NSString stringWithFormat:@"更新于：%@", [self.dateFormatter stringFromDate:self.snapshot.updatedAt]] toMenu:menu];
    } else if (self.lastError) {
        NSMenuItem *errorItem = [self addDisabledItem:self.lastError.localizedDescription toMenu:menu];
        errorItem.image = [NSImage imageWithSystemSymbolName:@"exclamationmark.triangle" accessibilityDescription:@"错误"];
    } else {
        [self addDisabledItem:@"正在读取额度…" toMenu:menu];
    }

    if (self.historyFileURL) {
        [menu addItem:NSMenuItem.separatorItem];
        NSMenuItem *historyItem = [[NSMenuItem alloc] initWithTitle:@"" action:nil keyEquivalent:@""];
        historyItem.view = [[QuotaTrendView alloc] initWithPoints:self.historyPoints
                                                 totalRecordCount:self.historyRecordCount];
        [menu addItem:historyItem];
    }

    [menu addItem:NSMenuItem.separatorItem];
    NSMenuItem *refreshItem = [[NSMenuItem alloc] initWithTitle:(self.loading ? @"正在刷新…" : @"立即刷新")
                                                         action:@selector(refresh)
                                                  keyEquivalent:@"r"];
    refreshItem.target = self;
    refreshItem.enabled = !self.loading;
    refreshItem.image = [NSImage imageWithSystemSymbolName:@"arrow.clockwise" accessibilityDescription:@"刷新"];
    [menu addItem:refreshItem];

    NSMenuItem *quitItem = [[NSMenuItem alloc] initWithTitle:@"退出" action:@selector(quit) keyEquivalent:@"q"];
    quitItem.target = self;
    [menu addItem:quitItem];
}

- (void)addWindow:(nullable QuotaWindow *)window fallbackName:(NSString *)fallbackName toMenu:(NSMenu *)menu {
    if (!window) return;
    NSString *name = [self windowNameForMinutes:window.durationMinutes fallback:fallbackName];
    NSMenuItem *usageItem = [self addDisabledItem:
        [NSString stringWithFormat:@"%@：剩余 %ld%%（已用 %ld%%）", name, (long)window.remainingPercent, (long)window.usedPercent]
                                             toMenu:menu];
    usageItem.image = [self quotaImageForRemainingPercent:window.remainingPercent];

    NSMenuItem *resetItem = [self addDisabledItem:
        [NSString stringWithFormat:@"重置：%@", [self.dateFormatter stringFromDate:window.resetsAt]]
                                             toMenu:menu];
    resetItem.indentationLevel = 2;
}

- (NSMenuItem *)addDisabledItem:(NSString *)title toMenu:(NSMenu *)menu {
    NSMenuItem *item = [[NSMenuItem alloc] initWithTitle:title action:nil keyEquivalent:@""];
    item.enabled = NO;
    [menu addItem:item];
    return item;
}

- (NSImage *)quotaImageForRemainingPercent:(NSInteger)remainingPercent {
    NSString *symbol = remainingPercent >= 50 ? @"circle.fill" :
                       remainingPercent >= 20 ? @"circle.lefthalf.filled" : @"exclamationmark.circle.fill";
    NSImage *image = [NSImage imageWithSystemSymbolName:symbol
                              accessibilityDescription:[NSString stringWithFormat:@"剩余 %ld%%", (long)remainingPercent]];
    image.template = YES;
    return image;
}

- (NSString *)windowNameForMinutes:(NSInteger)minutes fallback:(NSString *)fallback {
    if (minutes == 300) return @"5 小时";
    if (minutes == 10080) return @"7 天";
    if (minutes > 0 && minutes % 1440 == 0) return [NSString stringWithFormat:@"%ld 天", (long)(minutes / 1440)];
    if (minutes > 0 && minutes % 60 == 0) return [NSString stringWithFormat:@"%ld 小时", (long)(minutes / 60)];
    return fallback;
}

- (NSString *)formatBalance:(NSString *)value {
    NSDecimalNumber *number = [NSDecimalNumber decimalNumberWithString:value];
    if ([number isEqualToNumber:NSDecimalNumber.notANumber]) return value;
    NSNumberFormatter *formatter = [NSNumberFormatter new];
    formatter.numberStyle = NSNumberFormatterDecimalStyle;
    formatter.minimumFractionDigits = 0;
    formatter.maximumFractionDigits = 2;
    return [formatter stringFromNumber:number] ?: value;
}

- (NSString *)tooltipForSnapshot:(QuotaSnapshot *)snapshot {
    NSMutableArray<NSString *> *lines = [NSMutableArray arrayWithObject:@"Codex 剩余额度"];
    if (snapshot.primary) {
        [lines addObject:[NSString stringWithFormat:@"%@：%ld%%",
                          [self windowNameForMinutes:snapshot.primary.durationMinutes fallback:@"短窗口"],
                          (long)snapshot.primary.remainingPercent]];
    }
    if (snapshot.secondary) {
        [lines addObject:[NSString stringWithFormat:@"%@：%ld%%",
                          [self windowNameForMinutes:snapshot.secondary.durationMinutes fallback:@"长窗口"],
                          (long)snapshot.secondary.remainingPercent]];
    }
    return [lines componentsJoinedByString:@"\n"];
}

@end


int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSApplication *application = NSApplication.sharedApplication;
        AppDelegate *delegate = [AppDelegate new];
        application.delegate = delegate;
        [application run];
        (void)delegate;
    }
    return 0;
}
