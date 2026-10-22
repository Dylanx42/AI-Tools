#import <Cocoa/Cocoa.h>
#import "OpenCodexQuota.h"

static NSString *const QuotaHistoryHeader = @"recorded_at,primary_used_percent,primary_remaining_percent,primary_window_minutes,primary_resets_at,secondary_used_percent,secondary_remaining_percent,secondary_window_minutes,secondary_resets_at\n";
static const NSTimeInterval QuotaTrendWindowInterval = 7.0 * 24.0 * 60.0 * 60.0;
static const NSTimeInterval QuotaTrendGapThreshold = 6.0 * 60.0 * 60.0;
static const CGFloat QuotaTrendSmoothingSigma = 8.0;
static NSString *const QuotaSelectedAccountKey = @"OpenCodexMonitoredAccountID";

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

@interface QuotaTrendView : NSView <NSViewToolTipOwner>
@property(nonatomic, copy) NSArray<QuotaHistoryPoint *> *points;
@property(nonatomic, strong) NSDateFormatter *axisDateFormatter;
@property(nonatomic, copy) NSString *primaryName;
@property(nonatomic, copy) NSString *secondaryName;
@property(nonatomic, strong, nullable) NSDate *primaryPreviousResetAt;
@property(nonatomic, strong, nullable) NSDate *secondaryPreviousResetAt;
@property(nonatomic, strong, nullable) NSTrackingArea *chartTrackingArea;
@property(nonatomic) NSToolTipTag chartToolTipTag;
@property(nonatomic) NSUInteger hoveredPointIndex;
- (instancetype)initWithPoints:(NSArray<QuotaHistoryPoint *> *)points;
- (CGFloat)drawLegendAtX:(CGFloat)x y:(CGFloat)y color:(NSColor *)color text:(NSString *)text;
- (void)appendSmoothedPath:(NSBezierPath *)path throughPoints:(NSArray<NSValue *> *)points;
- (NSRect)chartPlotRect;
- (void)drawHoverSelectionInRect:(NSRect)chartRect positions:(NSArray<NSNumber *> *)positions;
- (NSArray<NSNumber *> *)displayPositionsForChartWidth:(CGFloat)width;
- (NSUInteger)nearestPointIndexForChartX:(CGFloat)x;
- (void)updateHoveredPointAtViewLocation:(NSPoint)location;
- (NSString *)tooltipTextForPointIndex:(NSUInteger)index;
- (BOOL)isWindowResetFrom:(QuotaHistoryPoint *)previous to:(QuotaHistoryPoint *)current primary:(BOOL)primary;
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
        _hoveredPointIndex = NSNotFound;
        self.accessibilityElement = YES;
        self.accessibilityRole = NSAccessibilityImageRole;
        self.accessibilityLabel = @"最近 7 天的剩余额度趋势。将鼠标移入图表绘图区查看横向最近采样点的时间和两个窗口额度；空心圆标记重置。图表下方显示两个窗口的上次重置时间。";
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

- (NSRect)chartPlotRect {
    return NSMakeRect(30, 43, NSWidth(self.bounds) - 34, 91);
}

- (void)updateTrackingAreas {
    [super updateTrackingAreas];

    if (self.chartTrackingArea) [self removeTrackingArea:self.chartTrackingArea];
    self.chartTrackingArea = nil;
    if (self.chartToolTipTag != 0) [self removeToolTip:self.chartToolTipTag];
    self.chartToolTipTag = 0;
    if (self.points.count == 0) return;

    NSTrackingAreaOptions options = NSTrackingMouseMoved |
        NSTrackingMouseEnteredAndExited | NSTrackingActiveAlways | NSTrackingInVisibleRect;
    self.chartTrackingArea = [[NSTrackingArea alloc] initWithRect:NSZeroRect
                                                         options:options
                                                           owner:self
                                                        userInfo:nil];
    [self addTrackingArea:self.chartTrackingArea];
    self.chartToolTipTag = [self addToolTipRect:[self chartPlotRect] owner:self userData:NULL];
}

- (void)viewDidMoveToWindow {
    [super viewDidMoveToWindow];
    self.window.acceptsMouseMovedEvents = YES;
    [self updateTrackingAreas];
}

- (void)mouseEntered:(NSEvent *)event {
    NSPoint location = [self convertPoint:event.locationInWindow fromView:nil];
    [self updateHoveredPointAtViewLocation:location];
}

- (void)mouseMoved:(NSEvent *)event {
    NSPoint location = [self convertPoint:event.locationInWindow fromView:nil];
    [self updateHoveredPointAtViewLocation:location];
}

- (void)mouseExited:(NSEvent *)event {
    (void)event;
    if (self.hoveredPointIndex == NSNotFound) return;
    self.hoveredPointIndex = NSNotFound;
    [self setNeedsDisplay:YES];
}

- (void)updateHoveredPointAtViewLocation:(NSPoint)location {
    if (!NSPointInRect(location, [self chartPlotRect])) {
        if (self.hoveredPointIndex != NSNotFound) {
            self.hoveredPointIndex = NSNotFound;
            [self setNeedsDisplay:YES];
        }
        return;
    }

    NSUInteger index = [self nearestPointIndexForChartX:location.x];
    if (index == NSNotFound || self.hoveredPointIndex == index) return;
    self.hoveredPointIndex = index;
    [self setNeedsDisplay:YES];
}

- (NSUInteger)nearestPointIndexForChartX:(CGFloat)x {
    if (self.points.count == 0) return NSNotFound;
    NSRect chartRect = [self chartPlotRect];
    NSArray<NSNumber *> *positions = [self displayPositionsForChartWidth:NSWidth(chartRect)];
    CGFloat localX = x - NSMinX(chartRect);
    NSUInteger nearestIndex = NSNotFound;
    CGFloat nearestDistance = CGFLOAT_MAX;
    for (NSUInteger index = 0; index < positions.count; index++) {
        CGFloat distance = fabs(localX - positions[index].doubleValue);
        if (distance < nearestDistance) {
            nearestDistance = distance;
            nearestIndex = index;
        }
    }
    return nearestIndex;
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
    NSString *changeCount = [NSString stringWithFormat:@"%lu 点 · 移入图表看数据", (unsigned long)self.points.count];
    NSSize countSize = [changeCount sizeWithAttributes:secondaryAttributes];
    [changeCount drawAtPoint:NSMakePoint(NSWidth(self.bounds) - countSize.width, 22)
              withAttributes:secondaryAttributes];

    NSRect chartRect = [self chartPlotRect];
    [self drawGridInRect:chartRect labelAttributes:secondaryAttributes];
    [self drawPreviousResetSummary];

    if (self.points.count == 0) {
        [self drawCenteredText:@"近 7 天暂无额度记录" inRect:chartRect attributes:secondaryAttributes];
        return;
    }

    NSArray<NSNumber *> *positions = [self displayPositionsForChartWidth:NSWidth(chartRect)];
    [self drawSeriesPrimary:NO color:NSColor.systemPurpleColor inRect:chartRect positions:positions];
    [self drawSeriesPrimary:YES color:NSColor.systemBlueColor inRect:chartRect positions:positions];
    [self drawHoverSelectionInRect:chartRect positions:positions];
    [self drawAxisInRect:chartRect positions:positions attributes:secondaryAttributes];
}

- (void)drawHoverSelectionInRect:(NSRect)chartRect positions:(NSArray<NSNumber *> *)positions {
    NSUInteger index = self.hoveredPointIndex;
    if (index == NSNotFound || index >= self.points.count) return;
    CGFloat x = NSMinX(chartRect) + positions[index].doubleValue;
    NSBezierPath *crosshair = [NSBezierPath bezierPath];
    CGFloat dash[] = {2.0, 2.0};
    [crosshair setLineDash:dash count:2 phase:0];
    [crosshair moveToPoint:NSMakePoint(x, NSMinY(chartRect))];
    [crosshair lineToPoint:NSMakePoint(x, NSMaxY(chartRect))];
    crosshair.lineWidth = 0.8;
    [[NSColor.secondaryLabelColor colorWithAlphaComponent:0.42] setStroke];
    [crosshair stroke];

    QuotaHistoryPoint *sample = self.points[index];
    NSArray<NSDictionary *> *series = @[
        @{ @"value": sample.secondaryRemainingPercent ?: NSNull.null,
           @"color": NSColor.systemPurpleColor },
        @{ @"value": sample.primaryRemainingPercent ?: NSNull.null,
           @"color": NSColor.systemBlueColor }
    ];
    for (NSDictionary *item in series) {
        id rawValue = item[@"value"];
        if (rawValue == NSNull.null) continue;
        CGFloat value = MAX(0.0, MIN(100.0, [rawValue doubleValue]));
        CGFloat y = NSMinY(chartRect) + (100.0 - value) / 100.0 * NSHeight(chartRect);
        NSColor *color = item[@"color"];
        [NSColor.windowBackgroundColor setFill];
        [[NSBezierPath bezierPathWithOvalInRect:NSMakeRect(x - 5, y - 5, 10, 10)] fill];
        [color setStroke];
        NSBezierPath *marker = [NSBezierPath bezierPathWithOvalInRect:NSMakeRect(x - 4, y - 4, 8, 8)];
        marker.lineWidth = 2;
        [marker stroke];
    }
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

- (NSString *)view:(NSView *)view
  stringForToolTip:(NSToolTipTag)tag
             point:(NSPoint)point
          userData:(void *)data {
    (void)view;
    (void)tag;
    (void)data;
    NSUInteger nearestIndex = self.hoveredPointIndex != NSNotFound
        ? self.hoveredPointIndex
        : [self nearestPointIndexForChartX:point.x];
    if (nearestIndex == NSNotFound) return @"";
    return [self tooltipTextForPointIndex:nearestIndex];
}

- (NSString *)tooltipTextForPointIndex:(NSUInteger)nearestIndex {
    if (nearestIndex >= self.points.count) return @"";
    QuotaHistoryPoint *sample = self.points[nearestIndex];
    NSMutableArray<NSString *> *lines = [NSMutableArray arrayWithObject:
        [NSString stringWithFormat:@"采样点：%@（最近横向点）",
         [self.axisDateFormatter stringFromDate:sample.recordedAt]]];
    if (sample.primaryRemainingPercent) {
        double remaining = sample.primaryRemainingPercent.doubleValue;
        [lines addObject:[NSString stringWithFormat:@"%@：剩余 %.0f%% · 已用 %.0f%%",
                          self.primaryName, remaining, 100.0 - remaining]];
    }
    if (sample.secondaryRemainingPercent) {
        double remaining = sample.secondaryRemainingPercent.doubleValue;
        [lines addObject:[NSString stringWithFormat:@"%@：剩余 %.0f%% · 已用 %.0f%%",
                          self.secondaryName, remaining, 100.0 - remaining]];
    }
    if (nearestIndex > 0) {
        QuotaHistoryPoint *previous = self.points[nearestIndex - 1];
        NSMutableArray<NSString *> *resetWindows = [NSMutableArray array];
        if ([self isWindowResetFrom:previous to:sample primary:YES]) [resetWindows addObject:self.primaryName];
        if ([self isWindowResetFrom:previous to:sample primary:NO]) [resetWindows addObject:self.secondaryName];
        [lines addObject:resetWindows.count > 0
            ? [NSString stringWithFormat:@"本采样重置：%@", [resetWindows componentsJoinedByString:@"、"]]
            : @"本采样未检测到重置"];
    } else {
        [lines addObject:@"首个采样点，无前值可比较"];
    }
    return [lines componentsJoinedByString:@"\n"];
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

- (void)drawSeriesPrimary:(BOOL)primary
                    color:(NSColor *)color
                   inRect:(NSRect)chartRect
                positions:(NSArray<NSNumber *> *)positions {
    NSBezierPath *line = [NSBezierPath bezierPath];
    line.lineWidth = 1.8;
    line.lineCapStyle = NSLineCapStyleRound;
    line.lineJoinStyle = NSLineJoinStyleRound;
    NSMutableArray<NSValue *> *resetStarts = [NSMutableArray array];
    NSMutableArray<NSValue *> *segmentPoints = [NSMutableArray array];
    NSPoint latestPoint = NSZeroPoint;
    BOOL hasLatestPoint = NO;

    for (NSUInteger index = 0; index < self.points.count; index++) {
        QuotaHistoryPoint *point = self.points[index];
        NSNumber *value = primary ? point.primaryRemainingPercent : point.secondaryRemainingPercent;
        if (!value) continue;

        CGFloat clampedValue = MAX(0.0, MIN(100.0, value.doubleValue));
        NSPoint displayPoint = NSMakePoint(NSMinX(chartRect) + positions[index].doubleValue,
                                           NSMinY(chartRect) + (100.0 - clampedValue) / 100.0 * NSHeight(chartRect));
        BOOL reset = index > 0 &&
            [self isWindowResetFrom:self.points[index - 1] to:point primary:primary];
        if (reset) {
            if (segmentPoints.count > 0) {
                [self appendSmoothedPath:line throughPoints:segmentPoints];
                [segmentPoints removeAllObjects];
            } else if (line.isEmpty) {
                [line moveToPoint:displayPoint];
            }
            // Keep the stroke continuous; reset markers explain the abrupt change.
            [line lineToPoint:displayPoint];
            [resetStarts addObject:[NSValue valueWithPoint:displayPoint]];
        }
        [segmentPoints addObject:[NSValue valueWithPoint:displayPoint]];
        latestPoint = displayPoint;
        hasLatestPoint = YES;
    }
    if (segmentPoints.count > 0) {
        [self appendSmoothedPath:line throughPoints:segmentPoints];
    }
    if (line.isEmpty) return;
    [[color colorWithAlphaComponent:0.10] setStroke];
    NSBezierPath *halo = [line copy];
    halo.lineWidth = 4;
    [halo stroke];
    [color setStroke];
    [line stroke];

    if (hasLatestPoint) {
        [NSColor.windowBackgroundColor setFill];
        [[NSBezierPath bezierPathWithOvalInRect:NSMakeRect(latestPoint.x - 5, latestPoint.y - 5, 10, 10)] fill];
        [color setFill];
        [[NSBezierPath bezierPathWithOvalInRect:NSMakeRect(latestPoint.x - 3, latestPoint.y - 3, 6, 6)] fill];
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

    NSMutableArray<NSNumber *> *sampleWidths = [NSMutableArray arrayWithCapacity:count];
    for (NSUInteger index = 0; index < count; index++) {
        CGFloat previousSpan = index > 0
            ? MAX(0, points[index].pointValue.x - points[index - 1].pointValue.x) : 0;
        CGFloat nextSpan = index + 1 < count
            ? MAX(0, points[index + 1].pointValue.x - points[index].pointValue.x) : 0;
        CGFloat sampleWidth = (previousSpan + nextSpan) / 2.0;
        [sampleWidths addObject:@(MAX(0.5, MIN(2.0 * QuotaTrendSmoothingSigma, sampleWidth)))];
    }

    NSMutableArray<NSValue *> *trendPoints = [NSMutableArray arrayWithCapacity:count];
    for (NSUInteger index = 0; index < count; index++) {
        NSPoint point = points[index].pointValue;
        if (count >= 4 && index > 0 && index + 1 < count) {
            CGFloat weightedY = 0;
            CGFloat totalWeight = 0;
            NSUInteger firstNeighbor = index;
            while (firstNeighbor > 0 &&
                   point.x - points[firstNeighbor - 1].pointValue.x <= 3.0 * QuotaTrendSmoothingSigma) {
                firstNeighbor -= 1;
            }
            NSUInteger lastNeighbor = index;
            while (lastNeighbor + 1 < count &&
                   points[lastNeighbor + 1].pointValue.x - point.x <= 3.0 * QuotaTrendSmoothingSigma) {
                lastNeighbor += 1;
            }
            for (NSUInteger neighborIndex = firstNeighbor; neighborIndex <= lastNeighbor; neighborIndex++) {
                NSPoint neighbor = points[neighborIndex].pointValue;
                CGFloat distance = neighbor.x - point.x;
                CGFloat normalizedDistance = distance / QuotaTrendSmoothingSigma;
                CGFloat weight = exp(-0.5 * normalizedDistance * normalizedDistance) *
                                 sampleWidths[neighborIndex].doubleValue;
                weightedY += neighbor.y * weight;
                totalWeight += weight;
            }
            if (totalWeight > 0) {
                // Smooth in screen space so dense samples settle into a visible trend.
                // Segment endpoints remain exact; callers split at reset edges only.
                point.y = weightedY / totalWeight;
            }
        }
        [trendPoints addObject:[NSValue valueWithPoint:point]];
    }

    NSPoint firstPoint = trendPoints.firstObject.pointValue;
    [path moveToPoint:firstPoint];
    if (count == 1) return;
    if (count == 2) {
        [path lineToPoint:trendPoints.lastObject.pointValue];
        return;
    }

    NSMutableArray<NSNumber *> *spans = [NSMutableArray arrayWithCapacity:count - 1];
    NSMutableArray<NSNumber *> *slopes = [NSMutableArray arrayWithCapacity:count - 1];
    BOOL hasDuplicatePositions = NO;
    for (NSUInteger index = 0; index + 1 < count; index++) {
        NSPoint left = trendPoints[index].pointValue;
        NSPoint right = trendPoints[index + 1].pointValue;
        CGFloat span = right.x - left.x;
        if (span <= 0.001) {
            hasDuplicatePositions = YES;
            break;
        }
        [spans addObject:@(span)];
        [slopes addObject:@((right.y - left.y) / span)];
    }
    if (hasDuplicatePositions) {
        // Duplicate display positions cannot define a stable spline; keep a filtered polyline.
        for (NSUInteger index = 1; index < count; index++) {
            [path lineToPoint:trendPoints[index].pointValue];
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
        NSPoint left = trendPoints[index].pointValue;
        NSPoint right = trendPoints[index + 1].pointValue;
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

    // Idle stretches are compressed horizontally. Naming each one on a 300-point
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
    NSMutableArray<NSMutableDictionary *> *runs = [NSMutableArray array];
    NSMutableDictionary *current = nil;
    for (NSUInteger index = 1; index < self.points.count; index++) {
        NSTimeInterval delta = [self.points[index].recordedAt timeIntervalSinceDate:self.points[index - 1].recordedAt];
        BOOL gap = delta > QuotaTrendGapThreshold;
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
        : (window ? [NSString stringWithFormat:@"已用 %ld%% · 重置时间暂无数据", (long)window.usedPercent] : @"暂无数据");
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

static NSString *QuotaReadStatus(QuotaSnapshot *snapshot, BOOL loading, NSError *error) {
    if (loading) return @"正在读取额度…";
    if (error) return snapshot ? @"更新失败 · 当前为上次数据" : @"额度读取失败 · 请尝试刷新";
    if (!snapshot) return @"等待额度数据";
    NSDateFormatter *formatter = [NSDateFormatter new];
    formatter.locale = [NSLocale localeWithLocaleIdentifier:@"zh_CN"];
    formatter.dateFormat = @"HH:mm:ss";
    return [NSString stringWithFormat:@"%@ 读取 · %@", [formatter stringFromDate:snapshot.updatedAt],
            snapshot.upstreamRefreshConfirmed ? @"来源 OpenCodex" : @"上游状态未提供"];
}

static NSString *QuotaResetCreditsText(QuotaResetCredits *credits, BOOL loading, NSError *error) {
    if (error) return @"重置券 暂不可用";
    if (!credits) return loading ? @"重置券 正在读取…" : @"重置券 暂无数据";
    NSString *text = [NSString stringWithFormat:@"重置券 %@ 张", credits.availableCount];
    if (credits.availableCount.integerValue > 0) {
        if (credits.expiries.count) {
            NSDateFormatter *formatter = [NSDateFormatter new];
            formatter.locale = [NSLocale localeWithLocaleIdentifier:@"zh_CN"];
            formatter.dateFormat = @"M/d HH:mm";
            text = [text stringByAppendingFormat:@" · %@%@ 到期", credits.availableCount.integerValue > 1 ? @"最近 " : @"",
                    [formatter stringFromDate:credits.expiries.firstObject]];
        } else {
            text = [text stringByAppendingString:@" · 到期时间暂无数据"];
        }
    }
    return loading ? [text stringByAppendingString:@" · 正在刷新"] : text;
}

@interface QuotaDashboardView : NSView
@property(nonatomic, strong) NSColor *statusColor;
@property(nonatomic) CGFloat footerY;
@property(nonatomic) CGFloat planBadgeWidth;
- (instancetype)initWithSnapshot:(QuotaSnapshot *)snapshot points:(NSArray<QuotaHistoryPoint *> *)points
                         loading:(BOOL)loading error:(NSError *)error
                    resetCredits:(QuotaResetCredits *)resetCredits creditsLoading:(BOOL)creditsLoading
                    creditsError:(NSError *)creditsError;
@end

@implementation QuotaDashboardView
- (BOOL)isFlipped { return YES; }

- (instancetype)initWithSnapshot:(QuotaSnapshot *)snapshot points:(NSArray<QuotaHistoryPoint *> *)points
                         loading:(BOOL)loading error:(NSError *)error
                    resetCredits:(QuotaResetCredits *)resetCredits creditsLoading:(BOOL)creditsLoading
                    creditsError:(NSError *)creditsError {
    self = [super initWithFrame:NSMakeRect(0, 0, 400, 490)];
    if (!self) return nil;
    QuotaLabel(self, @"OpenCodex", NSMakeRect(22, 18, 180, 22), 16, NSFontWeightSemibold, NSColor.labelColor);
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
                                                   name:QuotaWindowName(snapshot.primary.durationMinutes, @"5 小时")
                                                  color:NSColor.systemBlueColor
                                                  frame:NSMakeRect(22, 58, 356, 78)
                                                 first:YES]];
    [self addSubview:[[QuotaCardView alloc] initWithWindow:snapshot.secondary
                                                   name:QuotaWindowName(snapshot.secondary.durationMinutes, @"7 天")
                                                  color:NSColor.systemPurpleColor
                                                  frame:NSMakeRect(22, 154, 356, 78)
                                                 first:NO]];

    QuotaTrendView *trend = [[QuotaTrendView alloc] initWithPoints:points];
    trend.frame = NSMakeRect(16, 248, 368, 184);
    trend.primaryName = QuotaWindowName(snapshot.primary.durationMinutes, @"5 小时");
    trend.secondaryName = QuotaWindowName(snapshot.secondary.durationMinutes, @"7 天");
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

    NSString *creditsText = QuotaResetCreditsText(resetCredits, creditsLoading, creditsError);
    NSTextField *creditsLabel = QuotaLabel(self, creditsText, NSMakeRect(22, 440, 356, 16), 11,
                                           NSFontWeightMedium, creditsError ? NSColor.systemOrangeColor : NSColor.secondaryLabelColor);
    NSMutableArray<NSString *> *creditTips = [NSMutableArray arrayWithObject:creditsText];
    NSDateFormatter *creditFormatter = [NSDateFormatter new];
    creditFormatter.locale = [NSLocale localeWithLocaleIdentifier:@"zh_CN"];
    creditFormatter.dateFormat = @"yyyy/M/d HH:mm:ss";
    for (NSDate *expiry in resetCredits.expiries) [creditTips addObject:[creditFormatter stringFromDate:expiry]];
    if (resetCredits.availableCount.integerValue > (NSInteger)resetCredits.expiries.count) {
        [creditTips addObject:@"部分或全部重置券未返回到期时间"];
    }
    if (resetCredits.updatedAt) [creditTips addObject:[@"读取于 " stringByAppendingString:[creditFormatter stringFromDate:resetCredits.updatedAt]]];
    if (creditsError) [creditTips addObject:creditsError.localizedDescription];
    creditsLabel.toolTip = [creditTips componentsJoinedByString:@"\n"];
    _footerY = 466;
    NSString *status = QuotaReadStatus(snapshot, loading, error);
    _statusColor = loading ? NSColor.systemBlueColor : error ? NSColor.systemOrangeColor :
                   snapshot.upstreamRefreshConfirmed ? NSColor.systemGreenColor : NSColor.tertiaryLabelColor;
    NSTextField *statusLabel = QuotaLabel(self, status, NSMakeRect(34, _footerY, 378, 16), 11,
                                         NSFontWeightRegular, NSColor.secondaryLabelColor);
    statusLabel.frame = NSMakeRect(36, _footerY, 342, 16);
    statusLabel.toolTip = error.localizedDescription ?: (snapshot && !snapshot.upstreamRefreshConfirmed
        ? @"已读取 OpenCodex 返回的额度，但它未提供上游刷新确认；时间为本次本地读取时间，数值可能来自缓存。未确认值不记作新趋势点。"
        : status);
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

@interface AppDelegate : NSObject <NSApplicationDelegate, NSMenuDelegate>
@property(nonatomic, strong) OpenCodexQuotaService *service;
@property(nonatomic, strong) OpenCodexQuotaService *resetCreditService;
@property(nonatomic, strong, nullable) QuotaResetCredits *resetCredits;
@property(nonatomic, strong, nullable) NSError *resetCreditsError;
@property(nonatomic) BOOL resetCreditsLoading;
@property(nonatomic) NSUInteger resetCreditsRequestVersion;
@property(nonatomic, copy) NSArray<QuotaAccount *> *accounts;
@property(nonatomic, copy, nullable) NSString *selectedAccountID;
@property(nonatomic, strong) NSUserDefaults *preferences;
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
@property(nonatomic, strong, nullable) NSURL *historyDirectoryURL;
@property(nonatomic, copy, nullable) NSString *lastHistorySignature;
@property(nonatomic, strong) NSMutableArray<QuotaHistoryPoint *> *historyPoints;
- (void)trimChartPointsToTrendWindow;
@end

@implementation AppDelegate

- (instancetype)init {
    self = [super init];
    if (self) {
        _service = [OpenCodexQuotaService new];
        _resetCreditService = [[OpenCodexQuotaService alloc] initWithExecutableURL:nil timeout:15];
        _accounts = @[];
        _preferences = NSUserDefaults.standardUserDefaults;
        _selectedAccountID = [_preferences stringForKey:QuotaSelectedAccountKey];
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
    [self invalidateResetCredits];
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
    button.toolTip = @"正在读取 OpenCodex 额度";

    NSMenu *menu = [NSMenu new];
    menu.autoenablesItems = NO;
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
    [self.service fetch:^(NSArray<QuotaAccount *> *accounts, NSError *error) {
        typeof(self) self = weakSelf;
        if (!self) return;
        self.loading = NO;
        NSTimeInterval nextInterval = 60;
        QuotaAccount *account = nil;
        if (accounts) {
            self.accounts = accounts;
            account = QuotaSelectedAccount(accounts, self.selectedAccountID);
            if (account && !self.selectedAccountID.length) {
                self.selectedAccountID = account.accountID;
                [self.preferences setObject:self.selectedAccountID forKey:QuotaSelectedAccountKey];
                [self prepareUsageHistory];
            }
            if (!account) {
                [self invalidateResetCredits];
                self.snapshot = nil;
                self.historyFileURL = nil;
                [self.historyPoints removeAllObjects];
                error = QuotaError(QuotaErrorAccountUnavailable, accounts.count
                    ? @"监控账户已不在 OpenCodex 列表中，请在“监控账户”菜单重新选择。"
                    : @"OpenCodex 尚无 ChatGPT/Codex 账户，请先在 OpenCodex 中登录。");
            } else {
                error = account.refreshError;
                if (!self.historyFileURL) [self prepareUsageHistory];
            }
        }
        QuotaSnapshot *snapshot = account.snapshot;
        if (snapshot && !error) {
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
            // A cached reading may be shown, but is never recorded as a fresh sample.
            if (snapshot && !self.snapshot) self.snapshot = snapshot;
            self.consecutiveFailures += 1;
            self.lastError = error;
            nextInterval = [self nextFailureRefreshInterval];
            NSLog(@"CodexQuotaBar refresh failed: %@", error.localizedDescription);
        }

        [self updateStatusDisplay];
        if (account) [self refreshResetCredits];
        [self rebuildMenu];
        [self scheduleNextRefreshAfter:nextInterval];
    }];
}

- (void)selectMonitoredAccount:(NSMenuItem *)sender {
    if (self.loading || ![sender.representedObject isKindOfClass:NSString.class]) return;
    NSString *identifier = sender.representedObject;
    if ([identifier isEqualToString:self.selectedAccountID]) return;
    QuotaAccount *account = QuotaSelectedAccount(self.accounts, identifier);
    if (!account) return;
    [self invalidateResetCredits];
    self.selectedAccountID = identifier;
    [self.preferences setObject:identifier forKey:QuotaSelectedAccountKey];
    self.snapshot = account.snapshot;
    self.lastError = account.refreshError;
    self.lastRefreshCompletedAt = nil;
    self.unchangedRefreshCount = 0;
    self.consecutiveFailures = 0;
    [self prepareUsageHistory];
    [self refresh];
}

- (void)invalidateResetCredits {
    self.resetCreditsRequestVersion += 1;
    [self.resetCreditService cancel];
    self.resetCredits = nil;
    self.resetCreditsError = nil;
    self.resetCreditsLoading = NO;
}

- (void)refreshResetCredits {
    if (!self.selectedAccountID.length || self.resetCreditsLoading) return;
    NSString *accountID = self.selectedAccountID;
    NSUInteger version = ++self.resetCreditsRequestVersion;
    self.resetCreditsLoading = YES;
    self.resetCreditsError = nil;
    __weak typeof(self) weakSelf = self;
    [self.resetCreditService fetchResetCreditsForAccountID:accountID completion:^(QuotaResetCredits *credits, NSError *error) {
        typeof(self) self = weakSelf;
        if (!self || version != self.resetCreditsRequestVersion || ![accountID isEqualToString:self.selectedAccountID]) return;
        self.resetCreditsLoading = NO;
        // Do not present a stale coupon count as a successful read, or accept a mismatched identity.
        self.resetCredits = !error && [credits.accountID isEqualToString:accountID] ? credits : nil;
        self.resetCreditsError = error ?: (self.resetCredits ? nil : QuotaError(QuotaErrorProtocol, @"未取得所选账户的重置券信息。"));
        [self rebuildMenu];
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
    return NO;
}

- (BOOL)window:(nullable QuotaWindow *)window differsFrom:(nullable QuotaWindow *)previous {
    if (!window || !previous) return window != previous;
    return window.usedPercent != previous.usedPercent ||
           window.durationMinutes != previous.durationMinutes ||
           (window.resetsAt == nil) != (previous.resetsAt == nil) ||
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
    // Clear before opening another file, including on failure, so a new account
    // can never append to the previous account's CSV.
    self.historyFileURL = nil;
    self.lastHistorySignature = nil;
    [self.historyPoints removeAllObjects];
    if (!self.selectedAccountID.length) return;
    NSFileManager *fileManager = NSFileManager.defaultManager;
    NSError *error = nil;
    NSURL *directoryURL = self.historyDirectoryURL;
    if (!directoryURL) {
        NSURL *applicationSupportURL = [fileManager URLForDirectory:NSApplicationSupportDirectory
                                                       inDomain:NSUserDomainMask
                                              appropriateForURL:nil
                                                         create:YES
                                                          error:&error];
        if (!applicationSupportURL) {
            NSLog(@"CodexQuotaBar could not locate Application Support: %@", error.localizedDescription);
            return;
        }

        directoryURL = [[applicationSupportURL URLByAppendingPathComponent:@"CodexQuotaBar" isDirectory:YES]
                        URLByAppendingPathComponent:@"opencodex-accounts" isDirectory:YES];
        self.historyDirectoryURL = directoryURL;
    }
    if (![fileManager createDirectoryAtURL:directoryURL
               withIntermediateDirectories:YES
                                attributes:@{NSFilePosixPermissions: @0700}
                                     error:&error]) {
        NSLog(@"CodexQuotaBar could not create history directory: %@", error.localizedDescription);
        return;
    }

    NSURL *fileURL = [directoryURL URLByAppendingPathComponent:QuotaHistoryFileName(self.selectedAccountID) isDirectory:NO];
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
    return value == other || [value isEqual:other];
}

- (NSArray<NSString *> *)historyFieldsForWindow:(nullable QuotaWindow *)window {
    if (!window) return @[@"", @"", @"", @""];
    return @[
        [NSString stringWithFormat:@"%ld", (long)window.usedPercent],
        [NSString stringWithFormat:@"%ld", (long)window.remainingPercent],
        [NSString stringWithFormat:@"%ld", (long)window.durationMinutes],
        window.resetsAt ? [self.historyDateFormatter stringFromDate:window.resetsAt] : @""
    ];
}

- (void)recordSnapshotIfChanged:(QuotaSnapshot *)snapshot {
    if (!snapshot.upstreamRefreshConfirmed || ![snapshot.accountID isEqualToString:self.selectedAccountID]) return;
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
        NSString *primary = self.snapshot.primary ? [NSString stringWithFormat:@"%ld%%", (long)self.snapshot.primary.remainingPercent] : @"—";
        NSString *secondary = self.snapshot.secondary ? [NSString stringWithFormat:@"%ld%%", (long)self.snapshot.secondary.remainingPercent] : @"—";
        button.title = [NSString stringWithFormat:@"%@ · %@", primary, secondary];
        button.toolTip = [self tooltipForSnapshot:self.snapshot];
        if (self.lastError) button.toolTip = [button.toolTip stringByAppendingFormat:@"\n%@", self.lastError.localizedDescription];
        if (self.loading) button.toolTip = [button.toolTip stringByAppendingString:@"\n正在刷新…"];
    } else if (self.loading) {
        button.title = @"…";
        button.toolTip = @"正在读取 OpenCodex 额度";
    } else {
        button.title = @"!";
        button.toolTip = self.lastError.localizedDescription ?: @"额度读取失败";
    }
}

- (void)rebuildMenu {
    NSMenu *menu = self.statusItem.menu;
    [menu removeAllItems];

    QuotaAccount *selected = QuotaSelectedAccount(self.accounts, self.selectedAccountID);
    NSString *selection = selected.displayName ?: (self.selectedAccountID.length ? @"账户不可用，请重新选择" :
        (self.loading ? @"正在读取账户…" : @"暂无账户"));
    NSMenuItem *accountItem = [[NSMenuItem alloc] initWithTitle:[@"监控账户：" stringByAppendingString:selection]
                                                      action:nil keyEquivalent:@""];
    accountItem.image = [NSImage imageWithSystemSymbolName:@"person.crop.circle" accessibilityDescription:@"监控账户"];
    accountItem.toolTip = @"选择仅影响额度栏显示，不改变 OpenCodex 实际使用的账户。";
    NSMenu *accountMenu = [[NSMenu alloc] initWithTitle:@"监控账户"];
    accountMenu.autoenablesItems = NO;
    for (QuotaAccount *account in self.accounts) {
        NSString *title = account.active ? [account.displayName stringByAppendingString:@"（OpenCodex 当前）"] : account.displayName;
        NSMenuItem *item = [[NSMenuItem alloc] initWithTitle:title action:@selector(selectMonitoredAccount:) keyEquivalent:@""];
        item.target = self;
        item.representedObject = account.accountID;
        item.state = [account.accountID isEqualToString:self.selectedAccountID] ? NSControlStateValueOn : NSControlStateValueOff;
        item.enabled = !self.loading;
        item.toolTip = account.refreshError.localizedDescription ?: accountItem.toolTip;
        [accountMenu addItem:item];
    }
    if (!self.accounts.count) {
        NSMenuItem *empty = [[NSMenuItem alloc] initWithTitle:(self.loading ? @"正在读取…" : @"暂无账户，请检查 OpenCodex") action:nil keyEquivalent:@""];
        empty.enabled = NO;
        [accountMenu addItem:empty];
    }
    accountItem.submenu = accountMenu;
    [menu addItem:accountItem];
    [menu addItem:NSMenuItem.separatorItem];

    NSMenuItem *dashboardItem = [[NSMenuItem alloc] initWithTitle:@"额度概览" action:nil keyEquivalent:@""];
    dashboardItem.view = [[QuotaDashboardView alloc] initWithSnapshot:self.snapshot
                                                             points:self.historyPoints
                                                            loading:self.loading error:self.lastError
                                                       resetCredits:self.resetCredits creditsLoading:self.resetCreditsLoading
                                                       creditsError:self.resetCreditsError];
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
    QuotaAccount *selected = QuotaSelectedAccount(self.accounts, self.selectedAccountID);
    NSMutableArray<NSString *> *lines = [NSMutableArray arrayWithObjects:@"OpenCodex 剩余额度",
        selected.displayName ?: @"监控账户不可用", nil];
    if (!snapshot.upstreamRefreshConfirmed) [lines addObject:@"已读取额度；OpenCodex 未提供上游刷新状态，数值可能来自缓存。"];
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
