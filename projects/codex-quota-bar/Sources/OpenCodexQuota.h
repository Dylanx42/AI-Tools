#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

FOUNDATION_EXPORT NSString *const QuotaErrorDomain;
typedef NS_ENUM(NSInteger, QuotaErrorCode) {
    QuotaErrorCLIUnavailable = 1,
    QuotaErrorAlreadyRefreshing,
    QuotaErrorLaunchFailed,
    QuotaErrorProtocol,
    QuotaErrorTimedOut,
    QuotaErrorAccountUnavailable,
};
FOUNDATION_EXPORT NSError *QuotaError(QuotaErrorCode code, NSString *description);

@interface QuotaWindow : NSObject
@property(nonatomic) NSInteger usedPercent;
@property(nonatomic) NSInteger durationMinutes;
@property(nonatomic, strong, nullable) NSDate *resetsAt;
@property(nonatomic, readonly) NSInteger remainingPercent;
@end

@interface QuotaSnapshot : NSObject
@property(nonatomic, copy) NSString *accountID;
@property(nonatomic, strong, nullable) QuotaWindow *primary;
@property(nonatomic, strong, nullable) QuotaWindow *secondary;
@property(nonatomic, copy, nullable) NSString *planType;
@property(nonatomic, strong) NSDate *updatedAt;
@end

@interface QuotaAccount : NSObject
@property(nonatomic, copy) NSString *accountID;
@property(nonatomic, copy) NSString *displayName;
@property(nonatomic) BOOL active;
@property(nonatomic, strong, nullable) QuotaSnapshot *snapshot;
@property(nonatomic, strong, nullable) NSError *refreshError;
@end

// No credential or full upstream response is retained by these models.
FOUNDATION_EXPORT NSArray<QuotaAccount *> *_Nullable QuotaParseAccounts(NSData *data, NSError *_Nullable *_Nullable error);
FOUNDATION_EXPORT QuotaAccount *_Nullable QuotaSelectedAccount(NSArray<QuotaAccount *> *accounts,
                                                            NSString *_Nullable selectedID);
FOUNDATION_EXPORT NSString *QuotaHistoryFileName(NSString *accountID);

typedef void (^QuotaAccountsCompletion)(NSArray<QuotaAccount *> *_Nullable accounts,
                                        NSError *_Nullable error);

@interface OpenCodexQuotaService : NSObject
- (instancetype)init;
// Explicit executable and deadline also allow offline tests without a real login.
- (instancetype)initWithExecutableURL:(NSURL *_Nullable)executableURL
                             timeout:(NSTimeInterval)timeout;
- (void)fetch:(QuotaAccountsCompletion)completion;
- (void)cancel;
@end

NS_ASSUME_NONNULL_END
