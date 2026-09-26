#import <Cocoa/Cocoa.h>

static NSString *const QuotaErrorDomain = @"app.codexquotabar.desktop";
static NSString *const QuotaHistoryHeader = @"recorded_at,primary_used_percent,primary_remaining_percent,primary_window_minutes,primary_resets_at,secondary_used_percent,secondary_remaining_percent,secondary_window_minutes,secondary_resets_at\n";
static const NSTimeInterval QuotaTrendWindowInterval = 7.0 * 24.0 * 60.0 * 60.0;

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
@property(nonatomic, copy, nullable) NSArray<NSDate *> *resetCreditExpiries;
@property(nonatomic, strong) NSDate *updatedAt;
@end

@implementation QuotaSnapshot
@end

@interface QuotaHistoryPoint : NSObject
@property(nonatomic, strong) NSDate *recordedAt;
@property(nonatomic, strong, nullable) NSNumber *primaryRemainingPercent;
@property(nonatomic, strong, nullable) NSNumber *secondaryRemainingPercent;
@property(nonatomic, strong, nullable) NSDate *primaryResetsAt;
@property(nonatomic, strong, nullable) NSDate *secondaryResetsAt;
@end

@implementation QuotaHistoryPoint
@end

static NSDate *QuotaPreviousResetAt(QuotaWindow *window) {
    if (!window || !window.resetsAt || window.durationMinutes <= 0) return nil;
    NSTimeInterval windowDuration = (NSTimeInterval)window.durationMinutes * 60.0;
    return [window.resetsAt dateByAddingTimeInterval:-windowDuration];
}

static NSString *QuotaWindowName(NSInteger minutes, NSString *fallback) {
    if (minutes > 0 && minutes % 1440 == 0) return [NSString stringWithFormat:@"%ld 天", (long)(minutes / 1440)];
    if (minutes > 0 && minutes % 60 == 0) return [NSString stringWithFormat:@"%ld 小时", (long)(minutes / 60)];
    return fallback;
}

static NSTextField *QuotaLabel(NSView *parent, NSString *text, NSRect frame,
                               CGFloat size, NSFontWeight weight, NSColor *color) {
    NSTextField *label = [NSTextField labelWithString:text ?: @""];
    label.frame = frame;
    label.font = [NSFont systemFontOfSize:size weight:weight];
    label.textColor = color;
    label.lineBreakMode = NSLineBreakByTruncatingTail;
    [parent addSubview:label];
    return label;
}

@interface QuotaTrendView : NSView
@property(nonatomic, copy) NSArray<QuotaHistoryPoint *> *points;
@property(nonatomic, strong) NSDateFormatter *axisDateFormatter;
@property(nonatomic, copy) NSString *primaryName;
@property(nonatomic, copy) NSString *secondaryName;
@property(nonatomic, strong, nullable) NSDate *primaryPreviousResetAt;
@property(nonatomic, strong, nullable) NSDate *secondaryPreviousResetAt;
- (instancetype)initWithPoints:(NSArray<QuotaHistoryPoint *> *)points;
- (CGFloat)drawLegendAtX:(CGFloat)x y:(CGFloat)y color:(NSColor *)color text:(NSString *)text;
- (void)appendSmoothedPath:(NSBezierPath *)path throughPoints:(NSArray<NSValue *> *)points;
@end

@implementation QuotaTrendView

- (instancetype)initWithPoints:(NSArray<QuotaHistoryPoint *> *)points {
    self = [super initWithFrame:NSMakeRect(0, 0, 368, 184)];
    if (self) {
        _points = [points copy];
        _axisDateFormatter = [NSDateFormatter new];
        _axisDateFormatter.locale = [NSLocale localeWithLocaleIdentifier:@"zh_CN"];
        _axisDateFormatter.timeZone = NSTimeZone.localTimeZone;
        _axisDateFormatter.dateFormat = @"M/d HH:mm";
        _primaryName = @"5 小时";
        _secondaryName = @"7 天";
        self.accessibilityElement = YES;
        self.accessibilityRole = NSAccessibilityImageRole;
        self.accessibilityLabel = @"最近 7 天的剩余额度趋势，蓝色为短窗口，紫色为长窗口，纵轴为 0 到 100 百分比，空心圆标出额度窗口重置；图表下方显示两个额度窗口上一次重置时间";
        QuotaHistoryPoint *latest = points.lastObject;
        self.accessibilityValue = latest
            ? [NSString stringWithFormat:@"%lu 个变化点，短窗口 %@%%，长窗口 %@%%",
               (unsigned long)points.count, latest.primaryRemainingPercent ?: @"未知", latest.secondaryRemainingPercent ?: @"未知"]
            : @"等待首次额度记录";
    }
    return self;
}

- (BOOL)isFlipped {
    return YES;
}

- (void)drawRect:(NSRect)dirtyRect {
    [super drawRect:dirtyRect];

    NSDictionary *secondaryAttributes = @{
        NSFontAttributeName: [NSFont monospacedDigitSystemFontOfSize:9 weight:NSFontWeightMedium],
        NSForegroundColorAttributeName: NSColor.secondaryLabelColor
    };
    NSDictionary *titleAttributes = @{
        NSFontAttributeName: [NSFont systemFontOfSize:12 weight:NSFontWeightSemibold],
        NSForegroundColorAttributeName: NSColor.labelColor
    };
    [@"额度趋势" drawAtPoint:NSMakePoint(0, 0) withAttributes:titleAttributes];
    NSString *period = @"近 7 天";
    NSSize periodSize = [period sizeWithAttributes:secondaryAttributes];
    NSRect periodPill = NSMakeRect(NSWidth(self.bounds) - periodSize.width - 14, 0,
                                   periodSize.width + 14, 18);
    [[NSColor.labelColor colorWithAlphaComponent:0.055] setFill];
    [[NSBezierPath bezierPathWithRoundedRect:periodPill xRadius:9 yRadius:9] fill];
    [period drawAtPoint:NSMakePoint(NSMidX(periodPill) - periodSize.width / 2, 3)
         withAttributes:secondaryAttributes];

    CGFloat legendX = [self drawLegendAtX:0 y:20 color:NSColor.systemBlueColor text:self.primaryName];
    [self drawLegendAtX:legendX + 16 y:20 color:NSColor.systemPurpleColor text:self.secondaryName];
    NSString *changeCount = [NSString stringWithFormat:@"%lu 个变化点", (unsigned long)self.points.count];
    NSSize countSize = [changeCount sizeWithAttributes:secondaryAttributes];
    [changeCount drawAtPoint:NSMakePoint(NSWidth(self.bounds) - countSize.width, 22)
              withAttributes:secondaryAttributes];

    NSRect chartRect = NSMakeRect(30, 43, NSWidth(self.bounds) - 34, 91);
    [self drawGridInRect:chartRect labelAttributes:secondaryAttributes];
    [self drawPreviousResetSummary];

    if (self.points.count == 0) {
        [self drawCenteredText:@"近 7 天暂无额度记录" inRect:chartRect attributes:secondaryAttributes];
        return;
    }

    NSArray<NSNumber *> *positions = [self displayPositionsForChartWidth:NSWidth(chartRect)];
    [self drawSeriesPrimary:NO color:NSColor.systemPurpleColor inRect:chartRect positions:positions];
    [self drawSeriesPrimary:YES color:NSColor.systemBlueColor inRect:chartRect positions:positions];
    [self drawAxisInRect:chartRect positions:positions attributes:secondaryAttributes];
    self.toolTip = [self resetTooltip];
}

- (void)drawPreviousResetSummary {
    NSDictionary *titleAttributes = @{
        NSFontAttributeName: [NSFont systemFontOfSize:10 weight:NSFontWeightMedium],
        NSForegroundColorAttributeName: NSColor.secondaryLabelColor
    };
    NSDictionary *nameAttributes = @{
        NSFontAttributeName: [NSFont systemFontOfSize:10 weight:NSFontWeightSemibold],
        NSForegroundColorAttributeName: NSColor.secondaryLabelColor
    };
    NSDictionary *dateAttributes = @{
        NSFontAttributeName: [NSFont monospacedDigitSystemFontOfSize:10 weight:NSFontWeightMedium],
        NSForegroundColorAttributeName: NSColor.secondaryLabelColor
    };
    CGFloat y = 160;
    [@"上次重置" drawAtPoint:NSMakePoint(0, y) withAttributes:titleAttributes];

    NSArray<NSDictionary *> *windows = @[
        @{ @"name": self.primaryName ?: @"短窗口",
           @"date": self.primaryPreviousResetAt ?: NSNull.null,
           @"color": NSColor.systemBlueColor },
        @{ @"name": self.secondaryName ?: @"长窗口",
           @"date": self.secondaryPreviousResetAt ?: NSNull.null,
           @"color": NSColor.systemPurpleColor }
    ];
    NSArray<NSNumber *> *starts = @[@58, @212];
    for (NSUInteger index = 0; index < windows.count; index++) {
        NSDictionary *window = windows[index];
        CGFloat x = starts[index].doubleValue;
        [(NSColor *)window[@"color"] setFill];
        [[NSBezierPath bezierPathWithOvalInRect:NSMakeRect(x, y + 4, 5, 5)] fill];
        NSString *name = window[@"name"];
        [name drawAtPoint:NSMakePoint(x + 9, y) withAttributes:nameAttributes];
        CGFloat dateX = x + 9 + [name sizeWithAttributes:nameAttributes].width + 5;
        id dateValue = window[@"date"];
        NSString *date = dateValue == NSNull.null
            ? @"暂无数据"
            : [self.axisDateFormatter stringFromDate:(NSDate *)dateValue];
        [date drawAtPoint:NSMakePoint(dateX, y) withAttributes:dateAttributes];
    }
}

- (NSString *)resetTooltip {
    NSDateFormatter *formatter = [NSDateFormatter new];
    formatter.locale = [NSLocale localeWithLocaleIdentifier:@"zh_CN"];
    formatter.timeZone = NSTimeZone.localTimeZone;
    formatter.dateFormat = @"M/d HH:mm";
    NSMutableArray<NSString *> *lines = [NSMutableArray array];
    for (NSUInteger index = 1; index < self.points.count; index++) {
        QuotaHistoryPoint *previous = self.points[index - 1];
        QuotaHistoryPoint *current = self.points[index];
        NSMutableArray<NSString *> *windows = [NSMutableArray array];
        if ([self isWindowResetFrom:previous to:current primary:YES]) [windows addObject:self.primaryName];
        if ([self isWindowResetFrom:previous to:current primary:NO]) [windows addObject:self.secondaryName];
        if (windows.count == 0) continue;
        [lines addObject:[NSString stringWithFormat:@"%@ 重置 · %@",
                          [windows componentsJoinedByString:@"、"],
                          [formatter stringFromDate:current.recordedAt]]];
    }
    return lines.count ? [lines componentsJoinedByString:@"\n"] : @"这段记录里没有检测到额度窗口重置";
}

- (NSArray<NSNumber *> *)displayPositionsForChartWidth:(CGFloat)width {
    NSUInteger count = self.points.count;
    NSMutableArray<NSNumber *> *positions = [NSMutableArray arrayWithCapacity:count];
    if (count == 0) return positions;
    if (count == 1) {
        [positions addObject:@(width / 2.0)];
        return positions;
    }

    // Real clock time lets overnight gaps consume the axis. Each merged idle stretch
    // becomes one narrow break. Active width follows how far the quota actually moved.
    const CGFloat gapLane = 10.0;
    NSMutableArray<NSMutableDictionary *> *runs = [[self layoutRuns] mutableCopy];

    NSUInteger gapCount = 0;
    CGFloat activeWeight = 0;
    for (NSMutableDictionary *run in runs) {
        if ([run[@"gap"] boolValue]) {
            gapCount += 1;
            run[@"weight"] = @0;
        } else {
            NSUInteger steps = [run[@"steps"] unsignedIntegerValue];
            CGFloat swing = [run[@"swing"] doubleValue];
            CGFloat weight = MAX(0.55, sqrt(MAX(swing, 0)) * (0.85 + 0.15 * log2((CGFloat)steps + 1.0)));
            run[@"weight"] = @(weight);
            activeWeight += weight;
        }
    }

    CGFloat gapBudget = MIN(width * 0.12, gapLane * gapCount);
    CGFloat activeBudget = MAX(0, width - gapBudget);
    CGFloat lane = gapCount > 0 ? gapBudget / gapCount : 0;

    CGFloat cursor = 0;
    NSMutableArray<NSNumber *> *edges = [NSMutableArray arrayWithObject:@0];
    for (NSMutableDictionary *run in runs) {
        CGFloat runWidth = [run[@"gap"] boolValue]
            ? lane
            : (activeWeight > 0 ? [run[@"weight"] doubleValue] / activeWeight * activeBudget : 0);
        cursor += runWidth;
        [edges addObject:@(MIN(width, cursor))];
        run[@"width"] = @(runWidth);
    }
    edges[edges.count - 1] = @(width);

    [positions addObject:@0];
    NSUInteger edgeIndex = 1;
    for (NSDictionary *run in runs) {
        NSUInteger startIndex = [run[@"start"] unsignedIntegerValue];
        NSUInteger endIndex = [run[@"end"] unsignedIntegerValue];
        CGFloat left = edges[edgeIndex - 1].doubleValue;
        CGFloat right = edges[edgeIndex].doubleValue;
        NSUInteger steps = endIndex - startIndex;
        for (NSUInteger step = 1; step <= steps; step++) {
            CGFloat x = steps > 0 ? left + (CGFloat)step / (CGFloat)steps * (right - left) : right;
            [positions addObject:@(MIN(width, x))];
        }
        edgeIndex += 1;
    }
    while (positions.count < count) [positions addObject:@(width)];
    positions[count - 1] = @(width);
    return positions;
}

- (void)absorbQuietRunsBetweenGaps:(NSMutableArray<NSMutableDictionary *> *)runs {
    // A flat 3-point twitch trapped between two overnight breaks is not a usage
    // session. Fold it into the surrounding gap so the chart keeps one marker
    // instead of a row of overlapping labels.
    BOOL changed = YES;
    while (changed) {
        changed = NO;
        for (NSUInteger index = 1; index + 1 < runs.count; index++) {
            NSMutableDictionary *run = runs[index];
            NSMutableDictionary *before = runs[index - 1];
            NSMutableDictionary *after = runs[index + 1];
            BOOL quietBridge = ![run[@"gap"] boolValue] &&
                [before[@"gap"] boolValue] &&
                [after[@"gap"] boolValue] &&
                [run[@"swing"] doubleValue] < 12.0 &&
                [run[@"span"] doubleValue] < 8.0 * 60.0 * 60.0;
            if (!quietBridge) continue;
            before[@"end"] = after[@"end"];
            before[@"steps"] = @([before[@"steps"] unsignedIntegerValue] +
                                 [run[@"steps"] unsignedIntegerValue] +
                                 [after[@"steps"] unsignedIntegerValue]);
            before[@"span"] = @([before[@"span"] doubleValue] +
                                [run[@"span"] doubleValue] +
                                [after[@"span"] doubleValue]);
            [runs removeObjectAtIndex:index];
            [runs removeObjectAtIndex:index];
            changed = YES;
            break;
        }
    }
}

- (void)drawGridInRect:(NSRect)chartRect labelAttributes:(NSDictionary *)labelAttributes {
    for (NSNumber *level in @[@100, @50, @0]) {
        CGFloat y = NSMinY(chartRect) + (100.0 - level.doubleValue) / 100.0 * NSHeight(chartRect);
        NSString *label = [NSString stringWithFormat:@"%@%%", level];
        NSSize size = [label sizeWithAttributes:labelAttributes];
        [label drawAtPoint:NSMakePoint(NSMinX(chartRect) - size.width - 8, y - size.height / 2.0)
            withAttributes:labelAttributes];
        if (level.integerValue == 0) continue;
        NSBezierPath *gridLine = [NSBezierPath bezierPath];
        [gridLine moveToPoint:NSMakePoint(NSMinX(chartRect), y)];
        [gridLine lineToPoint:NSMakePoint(NSMaxX(chartRect), y)];
        gridLine.lineWidth = 1;
        [[NSColor.labelColor colorWithAlphaComponent:0.07] setStroke];
        [gridLine stroke];
    }
}

- (BOOL)isWindowResetFrom:(QuotaHistoryPoint *)previous to:(QuotaHistoryPoint *)current primary:(BOOL)primary {
    // Reset timestamps drift forward on every refresh. Only a large jump, paired
    // with the remaining quota returning to the top of the window, is a new period.
    NSDate *before = primary ? previous.primaryResetsAt : previous.secondaryResetsAt;
    NSDate *after = primary ? current.primaryResetsAt : current.secondaryResetsAt;
    NSNumber *beforeValue = primary ? previous.primaryRemainingPercent : previous.secondaryRemainingPercent;
    NSNumber *afterValue = primary ? current.primaryRemainingPercent : current.secondaryRemainingPercent;
    if (!before || !after || !beforeValue || !afterValue) return NO;
    BOOL resetMoved = [after timeIntervalSinceDate:before] > 30 * 60;
    BOOL quotaRestarted = beforeValue.doubleValue <= 25.0 && afterValue.doubleValue >= 80.0;
    return resetMoved && quotaRestarted;
}

- (CGFloat)quotaSwingFrom:(QuotaHistoryPoint *)previous to:(QuotaHistoryPoint *)current {
    CGFloat swing = 0;
    if (previous.primaryRemainingPercent && current.primaryRemainingPercent) {
        swing = fabs(current.primaryRemainingPercent.doubleValue - previous.primaryRemainingPercent.doubleValue);
    }
    if (previous.secondaryRemainingPercent && current.secondaryRemainingPercent) {
        swing = MAX(swing, fabs(current.secondaryRemainingPercent.doubleValue - previous.secondaryRemainingPercent.doubleValue));
    }
    return swing;
}

 - (NSIndexSet *)gapBreakIndexes {
    NSMutableIndexSet *breaks = [NSMutableIndexSet indexSet];
    for (NSDictionary *run in [self layoutRuns]) {
        if (![run[@"gap"] boolValue]) continue;
        NSUInteger end = [run[@"end"] unsignedIntegerValue];
        if (end > [run[@"start"] unsignedIntegerValue]) [breaks addIndex:end];
    }
    return breaks;
}

- (void)drawSeriesPrimary:(BOOL)primary
                    color:(NSColor *)color
                   inRect:(NSRect)chartRect
                positions:(NSArray<NSNumber *> *)positions {
    NSIndexSet *gapBreaks = [self gapBreakIndexes];
    NSBezierPath *line = [NSBezierPath bezierPath];
    line.lineWidth = 1.8;
    line.lineCapStyle = NSLineCapStyleRound;
    line.lineJoinStyle = NSLineJoinStyleRound;
    NSMutableArray<NSValue *> *segmentEnds = [NSMutableArray array];
    NSMutableArray<NSValue *> *resetStarts = [NSMutableArray array];
    NSMutableArray<NSValue *> *segmentPoints = [NSMutableArray array];
    NSPoint latestPoint = NSZeroPoint;
    BOOL hasLatestPoint = NO;

    for (NSUInteger index = 0; index < self.points.count; index++) {
        QuotaHistoryPoint *point = self.points[index];
        NSNumber *value = primary ? point.primaryRemainingPercent : point.secondaryRemainingPercent;
        BOOL breaksBefore = NO;
        if (index > 0) {
            breaksBefore = [gapBreaks containsIndex:index] ||
                [self isWindowResetFrom:self.points[index - 1] to:point primary:primary];
        }
        if (!value || breaksBefore) {
            if (segmentPoints.count > 0) {
                [self appendSmoothedPath:line throughPoints:segmentPoints];
                [segmentEnds addObject:segmentPoints.lastObject];
                [segmentPoints removeAllObjects];
            }
        }
        if (!value) continue;

        CGFloat clampedValue = MAX(0.0, MIN(100.0, value.doubleValue));
        NSPoint displayPoint = NSMakePoint(NSMinX(chartRect) + positions[index].doubleValue,
                                           NSMinY(chartRect) + (100.0 - clampedValue) / 100.0 * NSHeight(chartRect));
        if (segmentPoints.count == 0 && index > 0 &&
            [self isWindowResetFrom:self.points[index - 1] to:point primary:primary]) {
            [resetStarts addObject:[NSValue valueWithPoint:displayPoint]];
        }
        [segmentPoints addObject:[NSValue valueWithPoint:displayPoint]];
        latestPoint = displayPoint;
        hasLatestPoint = YES;
    }
    if (segmentPoints.count > 0) {
        [self appendSmoothedPath:line throughPoints:segmentPoints];
        [segmentEnds addObject:segmentPoints.lastObject];
    }
    if (line.isEmpty) return;
    [[color colorWithAlphaComponent:0.10] setStroke];
    NSBezierPath *halo = [line copy];
    halo.lineWidth = 4;
    [halo stroke];
    [color setStroke];
    [line stroke];

    for (NSValue *segmentEnd in segmentEnds) {
        NSPoint endPoint = segmentEnd.pointValue;
        BOOL latest = hasLatestPoint && NSEqualPoints(endPoint, latestPoint);
        if (!latest) continue;
        [NSColor.windowBackgroundColor setFill];
        [[NSBezierPath bezierPathWithOvalInRect:NSMakeRect(endPoint.x - 5, endPoint.y - 5, 10, 10)] fill];
        [color setFill];
        [[NSBezierPath bezierPathWithOvalInRect:NSMakeRect(endPoint.x - 3, endPoint.y - 3, 6, 6)] fill];
    }
    for (NSValue *resetStart in resetStarts) {
        NSPoint start = resetStart.pointValue;
        [NSColor.windowBackgroundColor setFill];
        [[NSBezierPath bezierPathWithOvalInRect:NSMakeRect(start.x - 5, start.y - 5, 10, 10)] fill];
        [color setStroke];
        NSBezierPath *ring = [NSBezierPath bezierPathWithOvalInRect:NSMakeRect(start.x - 3.5, start.y - 3.5, 7, 7)];
        ring.lineWidth = 1.7;
        [ring stroke];
    }
}

- (void)appendSmoothedPath:(NSBezierPath *)path throughPoints:(NSArray<NSValue *> *)points {
    NSUInteger count = points.count;
    if (count == 0) return;

    NSPoint firstPoint = points.firstObject.pointValue;
    [path moveToPoint:firstPoint];
    if (count == 1) return;
    if (count == 2) {
        [path lineToPoint:points.lastObject.pointValue];
        return;
    }

    NSMutableArray<NSNumber *> *spans = [NSMutableArray arrayWithCapacity:count - 1];
    NSMutableArray<NSNumber *> *slopes = [NSMutableArray arrayWithCapacity:count - 1];
    BOOL hasDuplicatePositions = NO;
    for (NSUInteger index = 0; index + 1 < count; index++) {
        NSPoint left = points[index].pointValue;
        NSPoint right = points[index + 1].pointValue;
        CGFloat span = right.x - left.x;
        if (span <= 0.001) {
            hasDuplicatePositions = YES;
            break;
        }
        [spans addObject:@(span)];
        [slopes addObject:@((right.y - left.y) / span)];
    }
    if (hasDuplicatePositions) {
        // Duplicate display positions cannot define a stable spline; preserve their exact shape.
        for (NSUInteger index = 1; index < count; index++) {
            [path lineToPoint:points[index].pointValue];
        }
        return;
    }

    NSMutableArray<NSNumber *> *tangents = [NSMutableArray arrayWithCapacity:count];
    for (NSUInteger index = 0; index < count; index++) [tangents addObject:@0];

    CGFloat firstSpan = spans[0].doubleValue;
    CGFloat secondSpan = spans[1].doubleValue;
    CGFloat firstSlope = slopes[0].doubleValue;
    CGFloat secondSlope = slopes[1].doubleValue;
    CGFloat firstTangent = ((2.0 * firstSpan + secondSpan) * firstSlope - firstSpan * secondSlope) /
                           (firstSpan + secondSpan);
    if (firstTangent * firstSlope <= 0) {
        firstTangent = 0;
    } else if (firstSlope * secondSlope < 0 && fabs(firstTangent) > 3.0 * fabs(firstSlope)) {
        firstTangent = 3.0 * firstSlope;
    }
    tangents[0] = @(firstTangent);

    for (NSUInteger index = 1; index + 1 < count; index++) {
        CGFloat previousSlope = slopes[index - 1].doubleValue;
        CGFloat nextSlope = slopes[index].doubleValue;
        if (previousSlope * nextSlope <= 0) {
            tangents[index] = @0;
            continue;
        }
        CGFloat previousSpan = spans[index - 1].doubleValue;
        CGFloat nextSpan = spans[index].doubleValue;
        CGFloat weight1 = 2.0 * nextSpan + previousSpan;
        CGFloat weight2 = nextSpan + 2.0 * previousSpan;
        CGFloat tangent = (weight1 + weight2) /
                          (weight1 / previousSlope + weight2 / nextSlope);
        tangents[index] = @(tangent);
    }

    CGFloat lastSpan = spans[count - 2].doubleValue;
    CGFloat previousSpan = spans[count - 3].doubleValue;
    CGFloat lastSlope = slopes[count - 2].doubleValue;
    CGFloat previousSlope = slopes[count - 3].doubleValue;
    CGFloat lastTangent = ((2.0 * lastSpan + previousSpan) * lastSlope - lastSpan * previousSlope) /
                          (lastSpan + previousSpan);
    if (lastTangent * lastSlope <= 0) {
        lastTangent = 0;
    } else if (lastSlope * previousSlope < 0 && fabs(lastTangent) > 3.0 * fabs(lastSlope)) {
        lastTangent = 3.0 * lastSlope;
    }
    tangents[count - 1] = @(lastTangent);

    for (NSUInteger index = 0; index + 1 < count; index++) {
        NSPoint left = points[index].pointValue;
        NSPoint right = points[index + 1].pointValue;
        CGFloat span = spans[index].doubleValue;
        CGFloat minimumY = MIN(left.y, right.y);
        CGFloat maximumY = MAX(left.y, right.y);
        NSPoint control1 = NSMakePoint(left.x + span / 3.0,
            left.y + tangents[index].doubleValue * span / 3.0);
        NSPoint control2 = NSMakePoint(right.x - span / 3.0,
            right.y - tangents[index + 1].doubleValue * span / 3.0);
        control1.y = MAX(minimumY, MIN(maximumY, control1.y));
        control2.y = MAX(minimumY, MIN(maximumY, control2.y));
        [path curveToPoint:right controlPoint1:control1 controlPoint2:control2];
    }
}

- (void)drawAxisInRect:(NSRect)chartRect
              positions:(NSArray<NSNumber *> *)positions
             attributes:(NSDictionary *)attributes {
    if (self.points.count == 1) {
        NSString *dateText = [self.axisDateFormatter stringFromDate:self.points.firstObject.recordedAt];
        NSSize dateSize = [dateText sizeWithAttributes:attributes];
        [dateText drawAtPoint:NSMakePoint(NSMidX(chartRect) - dateSize.width / 2, NSMaxY(chartRect) + 8)
               withAttributes:attributes];
        [self drawCenteredText:@"已记录起点，等待额度变化"
                       inRect:NSMakeRect(NSMinX(chartRect), NSMidY(chartRect) - 7, NSWidth(chartRect), 14)
                   attributes:attributes];
        return;
    }

    // Idle stretches are narrow breaks in the line. Naming each one on a 300-point
    // axis collides with the dates, so only the visible span is labeled.
    NSMutableIndexSet *indexes = [NSMutableIndexSet indexSet];
    [indexes addIndex:0];
    [indexes addIndex:self.points.count - 1];

    NSMutableArray<NSDictionary *> *labels = [NSMutableArray array];
    [indexes enumerateIndexesUsingBlock:^(NSUInteger index, BOOL *stop) {
        NSString *text = [self.axisDateFormatter stringFromDate:self.points[index].recordedAt];
        CGFloat center = NSMinX(chartRect) + positions[index].doubleValue;
        CGFloat width = [text sizeWithAttributes:attributes].width;
        BOOL startAligned = index == 0;
        BOOL endAligned = index + 1 == self.points.count;
        CGFloat x = startAligned ? NSMinX(chartRect) : endAligned ? NSMaxX(chartRect) - width : center - width / 2;
        x = MAX(NSMinX(chartRect), MIN(x, NSMaxX(chartRect) - width));
        [labels addObject:@{@"text": text, @"x": @(x), @"width": @(width)}];
        (void)stop;
    }];

    CGFloat cursor = -CGFLOAT_MAX;
    for (NSDictionary *label in labels) {
        CGFloat x = [label[@"x"] doubleValue];
        CGFloat width = [label[@"width"] doubleValue];
        if (x < cursor + 8) continue;
        [label[@"text"] drawAtPoint:NSMakePoint(x, NSMaxY(chartRect) + 8) withAttributes:attributes];
        cursor = x + width;
    }
}

- (NSArray<NSMutableDictionary *> *)layoutRuns {
    const NSTimeInterval gapThreshold = 6.0 * 60.0 * 60.0;
    NSMutableArray<NSMutableDictionary *> *runs = [NSMutableArray array];
    NSMutableDictionary *current = nil;
    for (NSUInteger index = 1; index < self.points.count; index++) {
        NSTimeInterval delta = [self.points[index].recordedAt timeIntervalSinceDate:self.points[index - 1].recordedAt];
        BOOL gap = delta > gapThreshold;
        CGFloat swing = [self quotaSwingFrom:self.points[index - 1] to:self.points[index]];
        if (!current || [current[@"gap"] boolValue] != gap) {
            current = [@{@"gap": @(gap), @"steps": @1, @"swing": @(swing), @"span": @(delta),
                         @"start": @(index - 1), @"end": @(index)} mutableCopy];
            [runs addObject:current];
        } else {
            current[@"steps"] = @([current[@"steps"] unsignedIntegerValue] + 1);
            current[@"swing"] = @([current[@"swing"] doubleValue] + swing);
            current[@"span"] = @([current[@"span"] doubleValue] + delta);
            current[@"end"] = @(index);
        }
    }
    [self absorbQuietRunsBetweenGaps:runs];
    return runs;
}

- (CGFloat)drawLegendAtX:(CGFloat)x y:(CGFloat)y color:(NSColor *)color text:(NSString *)text {
    [color setFill];
    [[NSBezierPath bezierPathWithOvalInRect:NSMakeRect(x, y + 5, 6, 6)] fill];
    NSDictionary *attributes = @{
        NSFontAttributeName: [NSFont systemFontOfSize:10 weight:NSFontWeightMedium],
        NSForegroundColorAttributeName: NSColor.secondaryLabelColor
    };
    [text drawAtPoint:NSMakePoint(x + 11, y) withAttributes:attributes];
    return x + 11 + [text sizeWithAttributes:attributes].width;
}

- (void)drawCenteredText:(NSString *)text
                   inRect:(NSRect)rect
               attributes:(NSDictionary *)attributes {
    NSSize size = [text sizeWithAttributes:attributes];
    [text drawAtPoint:NSMakePoint(NSMidX(rect) - size.width / 2, NSMidY(rect) - size.height / 2)
        withAttributes:attributes];
}

@end

@interface QuotaCardView : NSView
@property(nonatomic, strong) QuotaWindow *quotaWindow;
@property(nonatomic, strong) NSColor *accent;
- (instancetype)initWithWindow:(QuotaWindow *)window
                          name:(NSString *)name
                         color:(NSColor *)color
                         frame:(NSRect)frame
                         first:(BOOL)first;
@end

@implementation QuotaCardView
- (BOOL)isFlipped { return YES; }

- (instancetype)initWithWindow:(QuotaWindow *)window
                          name:(NSString *)name
                         color:(NSColor *)color
                         frame:(NSRect)frame
                         first:(BOOL)first {
    self = [super initWithFrame:frame];
    if (!self) return nil;
    _quotaWindow = window;
    _accent = color;
    NSTextField *nameLabel = QuotaLabel(self, name, NSMakeRect(0, 0, 150, 18),
                                        13, NSFontWeightSemibold, NSColor.secondaryLabelColor);
    NSString *value = window ? [NSString stringWithFormat:@"%ld%%", (long)window.remainingPercent] : @"—";
    NSTextField *number = QuotaLabel(self, value, NSMakeRect(150, -6, NSWidth(frame) - 150, 44), 36,
                                   NSFontWeightBold, window ? NSColor.labelColor : NSColor.tertiaryLabelColor);
    number.font = [NSFont monospacedDigitSystemFontOfSize:36 weight:NSFontWeightBold];
    number.alignment = NSTextAlignmentRight;
    NSDateFormatter *formatter = [NSDateFormatter new];
    formatter.locale = [NSLocale localeWithLocaleIdentifier:@"zh_CN"];
    formatter.dateFormat = @"M/d HH:mm";
    NSString *reset = window.resetsAt
        ? [NSString stringWithFormat:@"%@ 重置 · 已用 %ld%%", [formatter stringFromDate:window.resetsAt], (long)window.usedPercent]
        : @"窗口暂不可用";
    QuotaLabel(self, reset, NSMakeRect(0, 38, NSWidth(frame), 16),
               11, NSFontWeightRegular, NSColor.secondaryLabelColor);
    self.toolTip = reset;
    self.accessibilityLabel = [NSString stringWithFormat:@"%@ 剩余 %@%%，%@", name, value, reset];
    return self;
}

- (void)drawRect:(NSRect)dirtyRect {
    [super drawRect:dirtyRect];
    if (!self.quotaWindow) return;
    NSColor *fill = self.quotaWindow.remainingPercent <= 10 ? NSColor.systemRedColor :
                    self.quotaWindow.remainingPercent <= 20 ? NSColor.systemOrangeColor : self.accent;
    NSRect track = NSMakeRect(0, 64, NSWidth(self.bounds), 5);
    [[fill colorWithAlphaComponent:0.12] setFill];
    [[NSBezierPath bezierPathWithRoundedRect:track xRadius:2.5 yRadius:2.5] fill];
    if (self.quotaWindow.remainingPercent <= 0) return;
    track.size.width *= self.quotaWindow.remainingPercent / 100.0;
    [fill setFill];
    [[NSBezierPath bezierPathWithRoundedRect:track xRadius:2.5 yRadius:2.5] fill];
}
@end

@interface QuotaDashboardView : NSView
@property(nonatomic, strong) NSColor *statusColor;
@property(nonatomic) CGFloat footerY;
@property(nonatomic) CGFloat planBadgeWidth;
- (instancetype)initWithSnapshot:(QuotaSnapshot *)snapshot points:(NSArray<QuotaHistoryPoint *> *)points
                         loading:(BOOL)loading error:(NSError *)error;
@end

@implementation QuotaDashboardView
- (BOOL)isFlipped { return YES; }

- (instancetype)initWithSnapshot:(QuotaSnapshot *)snapshot points:(NSArray<QuotaHistoryPoint *> *)points
                         loading:(BOOL)loading error:(NSError *)error {
    self = [super initWithFrame:NSMakeRect(0, 0, 400, 466)];
    if (!self) return nil;
    QuotaLabel(self, @"Codex", NSMakeRect(22, 18, 180, 22), 16, NSFontWeightSemibold, NSColor.labelColor);
    if (snapshot.planType.length) {
        NSString *planName = snapshot.planType.uppercaseString;
        _planBadgeWidth = MIN(96, [planName sizeWithAttributes:@{NSFontAttributeName:[NSFont systemFontOfSize:10 weight:NSFontWeightSemibold]}].width + 16);
        NSTextField *plan = QuotaLabel(self, planName, NSMakeRect(370 - _planBadgeWidth, 20, _planBadgeWidth, 16),
                                       11, NSFontWeightSemibold, NSColor.secondaryLabelColor);
        plan.font = [NSFont systemFontOfSize:10 weight:NSFontWeightSemibold];
        plan.alignment = NSTextAlignmentCenter;
        plan.toolTip = [NSString stringWithFormat:@"当前套餐：%@", snapshot.planType];
    }
    [self addSubview:[[QuotaCardView alloc] initWithWindow:snapshot.primary
                                                   name:QuotaWindowName(snapshot.primary.durationMinutes, @"短窗口")
                                                  color:NSColor.systemBlueColor
                                                  frame:NSMakeRect(22, 58, 356, 78)
                                                 first:YES]];
    [self addSubview:[[QuotaCardView alloc] initWithWindow:snapshot.secondary
                                                   name:QuotaWindowName(snapshot.secondary.durationMinutes, @"长窗口")
                                                  color:NSColor.systemPurpleColor
                                                  frame:NSMakeRect(22, 154, 356, 78)
                                                 first:NO]];

    QuotaTrendView *trend = [[QuotaTrendView alloc] initWithPoints:points];
    trend.frame = NSMakeRect(16, 248, 368, 184);
    trend.primaryName = QuotaWindowName(snapshot.primary.durationMinutes, @"短窗口");
    trend.secondaryName = QuotaWindowName(snapshot.secondary.durationMinutes, @"长窗口");
    trend.primaryPreviousResetAt = QuotaPreviousResetAt(snapshot.primary);
    trend.secondaryPreviousResetAt = QuotaPreviousResetAt(snapshot.secondary);
    NSDateFormatter *previousResetFormatter = [NSDateFormatter new];
    previousResetFormatter.locale = [NSLocale localeWithLocaleIdentifier:@"zh_CN"];
    previousResetFormatter.timeZone = NSTimeZone.localTimeZone;
    previousResetFormatter.dateFormat = @"M/d HH:mm";
    NSString *primaryPreviousReset = trend.primaryPreviousResetAt
        ? [previousResetFormatter stringFromDate:trend.primaryPreviousResetAt] : @"暂无数据";
    NSString *secondaryPreviousReset = trend.secondaryPreviousResetAt
        ? [previousResetFormatter stringFromDate:trend.secondaryPreviousResetAt] : @"暂无数据";
    trend.accessibilityValue = [NSString stringWithFormat:@"%@；%@上次重置 %@，%@上次重置 %@",
                                trend.accessibilityValue, trend.primaryName, primaryPreviousReset,
                                trend.secondaryName, secondaryPreviousReset];
    [self addSubview:trend];

    NSMutableArray<NSString *> *details = [NSMutableArray array];
    NSString *resetCreditTip = nil;
    if (snapshot.creditBalance.length) {
        NSDecimalNumber *balance = [NSDecimalNumber decimalNumberWithString:snapshot.creditBalance];
        NSNumberFormatter *formatter = [NSNumberFormatter new];
        formatter.numberStyle = NSNumberFormatterDecimalStyle;
        formatter.maximumFractionDigits = 2;
        NSString *value = [balance isEqual:NSDecimalNumber.notANumber] ? snapshot.creditBalance : [formatter stringFromNumber:balance];
        [details addObject:[NSString stringWithFormat:@"Credits %@", value]];
    }
    if (snapshot.resetCreditCount) {
        NSDateFormatter *expiryFormatter = [NSDateFormatter new];
        expiryFormatter.locale = [NSLocale localeWithLocaleIdentifier:@"zh_CN"];
        expiryFormatter.dateFormat = @"M/d HH:mm";
        NSMutableArray<NSString *> *expiries = [NSMutableArray array];
        for (NSDate *expiry in snapshot.resetCreditExpiries) {
            [expiries addObject:[expiryFormatter stringFromDate:expiry]];
        }
        NSString *creditText = [NSString stringWithFormat:@"重置券 %@", snapshot.resetCreditCount];
        NSString *creditTip = nil;
        if (expiries.count == 1) {
            creditText = [creditText stringByAppendingFormat:@" · %@ 到期", expiries.firstObject];
        } else if (expiries.count > 1) {
            creditText = [creditText stringByAppendingFormat:@" · 最近 %@ 到期", expiries.firstObject];
            creditTip = [NSString stringWithFormat:@"重置券到期：%@", [expiries componentsJoinedByString:@"、"]];
            if (snapshot.resetCreditCount.integerValue > (NSInteger)expiries.count) {
                creditTip = [creditTip stringByAppendingString:@"；其余券未返回到期时间"];
            }
        }
        [details addObject:creditText];
        resetCreditTip = creditTip;
    }
    _footerY = 442;
    if (details.count) {
        NSTextField *detailLabel = QuotaLabel(self, [details componentsJoinedByString:@"    "],
                                             NSMakeRect(22, 440, 356, 16), 11, NSFontWeightMedium, NSColor.secondaryLabelColor);
        detailLabel.toolTip = resetCreditTip ?: detailLabel.stringValue;
        _footerY = 466;
        [self setFrameSize:NSMakeSize(400, 490)];
    }
    NSDateFormatter *updated = [NSDateFormatter new];
    updated.locale = [NSLocale localeWithLocaleIdentifier:@"zh_CN"];
    updated.dateFormat = @"HH:mm:ss";
    NSString *status = loading ? @"正在更新额度…" : error ? (snapshot ? @"更新失败 · 当前为上次数据" : @"额度读取失败 · 请尝试刷新") :
        snapshot ? [NSString stringWithFormat:@"%@ 更新", [updated stringFromDate:snapshot.updatedAt]] : @"等待额度数据";
    _statusColor = loading ? NSColor.systemBlueColor : error ? NSColor.systemOrangeColor :
                   snapshot ? NSColor.systemGreenColor : NSColor.tertiaryLabelColor;
    NSTextField *statusLabel = QuotaLabel(self, status, NSMakeRect(34, _footerY, 378, 16), 11,
                                         NSFontWeightRegular, NSColor.secondaryLabelColor);
    statusLabel.frame = NSMakeRect(36, _footerY, 342, 16);
    statusLabel.toolTip = error.localizedDescription ?: status;
    if (error) {
        NSTextField *errorLabel = QuotaLabel(self, error.localizedDescription,
                                            NSMakeRect(22, _footerY + 22, 356, 32), 11,
                                            NSFontWeightRegular, NSColor.secondaryLabelColor);
        errorLabel.maximumNumberOfLines = 2;
        errorLabel.cell.wraps = YES;
        errorLabel.toolTip = error.localizedDescription;
        [self setFrameSize:NSMakeSize(400, _footerY + 60)];
    }
    self.toolTip = error.localizedDescription;
    return self;
}

- (void)drawRect:(NSRect)dirtyRect {
    [super drawRect:dirtyRect];
    if (self.planBadgeWidth > 0) {
        [[NSColor.labelColor colorWithAlphaComponent:0.06] setFill];
        [[NSBezierPath bezierPathWithRoundedRect:NSMakeRect(366 - self.planBadgeWidth, 17, self.planBadgeWidth + 8, 22)
                                        xRadius:10 yRadius:10] fill];
    }
    [self.statusColor setFill];
    [[NSBezierPath bezierPathWithOvalInRect:NSMakeRect(22, self.footerY + 5, 6, 6)] fill];
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
    snapshot.resetCreditExpiries = [self resetCreditExpiries:resetCredits[@"credits"]];
    snapshot.updatedAt = [NSDate date];
    return snapshot;
}

- (NSArray<NSDate *> *)resetCreditExpiries:(id)value {
    // The service may omit the detail rows or cap them. A count without rows is
    // still valid; only known, future-or-present expiry timestamps are displayed.
    if (![value isKindOfClass:NSArray.class]) return @[];
    NSMutableArray<NSDate *> *expiries = [NSMutableArray array];
    for (id credit in (NSArray *)value) {
        if (![credit isKindOfClass:NSDictionary.class]) continue;
        id timestamp = credit[@"expiresAt"];
        if (![timestamp isKindOfClass:NSNumber.class] || [timestamp doubleValue] <= 0) continue;
        [expiries addObject:[NSDate dateWithTimeIntervalSince1970:[timestamp doubleValue]]];
    }
    [expiries sortUsingComparator:^NSComparisonResult(NSDate *left, NSDate *right) {
        return [left compare:right];
    }];
    return expiries;
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
@property(nonatomic, strong) NSISO8601DateFormatter *historyDateFormatter;
@property(nonatomic, strong, nullable) NSURL *historyFileURL;
@property(nonatomic, copy, nullable) NSString *lastHistorySignature;
@property(nonatomic, strong) NSMutableArray<QuotaHistoryPoint *> *historyPoints;
- (void)trimChartPointsToTrendWindow;
@end

@implementation AppDelegate

- (instancetype)init {
    self = [super init];
    if (self) {
        _service = [CodexQuotaService new];
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
    if (![snapshot.resetCreditCount isEqualToNumber:previous.resetCreditCount]) return YES;
    return ![self dates:snapshot.resetCreditExpiries equal:previous.resetCreditExpiries];
}

- (BOOL)dates:(nullable NSArray<NSDate *> *)dates equal:(nullable NSArray<NSDate *> *)previous {
    if (dates.count != previous.count) return NO;
    for (NSUInteger index = 0; index < dates.count; index++) {
        if (fabs([dates[index] timeIntervalSinceDate:previous[index]]) > 1) return NO;
    }
    return YES;
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
            if (columns[4].length > 0) point.primaryResetsAt = [self.historyDateFormatter dateFromString:columns[4]];
            if (columns[6].length > 0) point.secondaryRemainingPercent = @(columns[6].integerValue);
            if (columns[8].length > 0) point.secondaryResetsAt = [self.historyDateFormatter dateFromString:columns[8]];
            [self appendChartPoint:point];
        }
        self.lastHistorySignature = signature;
    }
}

- (void)appendChartPoint:(QuotaHistoryPoint *)point {
    // Reset timestamps drift forward on every refresh while the remaining quota
    // stays unchanged. The chart only needs the samples where a percentage moves.
    QuotaHistoryPoint *previous = self.historyPoints.lastObject;
    BOOL sameQuota = previous &&
        [self chartNumber:previous.primaryRemainingPercent equals:point.primaryRemainingPercent] &&
        [self chartNumber:previous.secondaryRemainingPercent equals:point.secondaryRemainingPercent];
    if (sameQuota) {
        previous.recordedAt = point.recordedAt;
        previous.primaryResetsAt = point.primaryResetsAt;
        previous.secondaryResetsAt = point.secondaryResetsAt;
        [self trimChartPointsToTrendWindow];
        return;
    }
    [self.historyPoints addObject:point];
    [self trimChartPointsToTrendWindow];
}

- (void)trimChartPointsToTrendWindow {
    // Keep the chart cache date-based; the CSV remains the complete local history.
    QuotaHistoryPoint *latest = self.historyPoints.lastObject;
    if (!latest) return;
    NSDate *cutoff = [latest.recordedAt dateByAddingTimeInterval:-QuotaTrendWindowInterval];
    NSUInteger firstIndex = 0;
    while (firstIndex < self.historyPoints.count &&
           [self.historyPoints[firstIndex].recordedAt compare:cutoff] == NSOrderedAscending) {
        firstIndex += 1;
    }
    if (firstIndex > 0) {
        [self.historyPoints removeObjectsInRange:NSMakeRange(0, firstIndex)];
    }
}

- (BOOL)chartNumber:(nullable NSNumber *)value equals:(nullable NSNumber *)other {
    return value == other || [value isEqualToNumber:other];
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
    QuotaHistoryPoint *point = [QuotaHistoryPoint new];
    point.recordedAt = snapshot.updatedAt;
    if (snapshot.primary) {
        point.primaryRemainingPercent = @(snapshot.primary.remainingPercent);
        point.primaryResetsAt = snapshot.primary.resetsAt;
    }
    if (snapshot.secondary) {
        point.secondaryRemainingPercent = @(snapshot.secondary.remainingPercent);
        point.secondaryResetsAt = snapshot.secondary.resetsAt;
    }
    [self appendChartPoint:point];
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

    NSMenuItem *dashboardItem = [[NSMenuItem alloc] initWithTitle:@"额度概览" action:nil keyEquivalent:@""];
    dashboardItem.view = [[QuotaDashboardView alloc] initWithSnapshot:self.snapshot
                                                             points:self.historyPoints
                                                            loading:self.loading error:self.lastError];
    [menu addItem:dashboardItem];

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
    quitItem.image = [NSImage imageWithSystemSymbolName:@"power" accessibilityDescription:@"退出"];
    [menu addItem:quitItem];
}

- (NSString *)windowNameForMinutes:(NSInteger)minutes fallback:(NSString *)fallback {
    return QuotaWindowName(minutes, fallback);
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
