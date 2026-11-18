import Darwin
import Foundation
import Security
import SystemConfiguration

struct IPv4Configuration: Equatable {
    private static let methodKey = kSCPropNetIPv4ConfigMethod as String
    private static let addressesKey = kSCPropNetIPv4Addresses as String
    private static let masksKey = kSCPropNetIPv4SubnetMasks as String
    private static let routerKey = kSCPropNetIPv4Router as String

    let values: [String: Any]

    var method: String { values[Self.methodKey] as? String ?? "" }
    var isManual: Bool { method == kSCValNetIPv4ConfigMethodManual as String }
    var address: String { (values[Self.addressesKey] as? [String])?.first ?? "" }
    var mask: String { (values[Self.masksKey] as? [String])?.first ?? "" }
    var router: String { values[Self.routerKey] as? String ?? "" }

    var modeLabel: String {
        switch method {
        case "DHCP": return "DHCP"
        case "Manual": return "手动"
        case "None": return "关闭 IPv4"
        case "": return "未配置"
        default: return method
        }
    }

    func settingManual(_ settings: ManualIPv4) -> Self {
        var updated = withoutAddresses()
        updated[Self.methodKey] = kSCValNetIPv4ConfigMethodManual as String
        updated[Self.addressesKey] = [settings.address]
        updated[Self.masksKey] = [settings.mask]
        if let gateway = settings.gateway { updated[Self.routerKey] = gateway }
        return Self(values: updated)
    }

    func settingDHCP() -> Self {
        var updated = withoutAddresses()
        updated[Self.methodKey] = kSCValNetIPv4ConfigMethodDHCP as String
        return Self(values: updated)
    }

    private func withoutAddresses() -> [String: Any] {
        var updated = values
        for key in [Self.addressesKey, Self.masksKey, Self.routerKey,
                    kSCPropNetIPv4BroadcastAddresses as String, kSCPropNetIPv4DestAddresses as String] {
            updated.removeValue(forKey: key)
        }
        return updated
    }

    static func == (lhs: Self, rhs: Self) -> Bool {
        NSDictionary(dictionary: lhs.values).isEqual(to: rhs.values)
    }
}

struct ManualIPv4 {
    let address: String
    let mask: String
    let gateway: String?

    init?(address: String, mask: String, gateway: String) {
        let address = address.trimmingCharacters(in: .whitespacesAndNewlines)
        let mask = mask.trimmingCharacters(in: .whitespacesAndNewlines)
        let gateway = gateway.trimmingCharacters(in: .whitespacesAndNewlines)
        guard validIP(address), validMask(mask), gateway.isEmpty || validIP(gateway) else { return nil }
        self.address = address
        self.mask = mask
        self.gateway = gateway.isEmpty ? nil : gateway
    }
}

func validIP(_ value: String) -> Bool {
    guard !value.utf8.contains(0) else { return false }
    var address = in_addr()
    return value.withCString { inet_pton(AF_INET, $0, &address) } == 1
}

func validMask(_ value: String) -> Bool {
    guard validIP(value) else { return false }
    let parts = value.split(separator: ".").compactMap { UInt32($0) }
    guard parts.count == 4 else { return false }
    let mask = parts.reduce(UInt32(0)) { ($0 << 8) | $1 }
    let inverted = ~mask
    return mask != 0 && (inverted &+ 1) & inverted == 0
}

struct Service {
    let locationID: String
    let id: String
    let name: String
    let device: String
    let enabled: Bool
    let ipv4Enabled: Bool
    let config: IPv4Configuration
    let current: IPv4Configuration

    var canConfigure: Bool { enabled && ipv4Enabled }
    var recoveryKey: String { "\(locationID)/\(id)" }
}

private let preferencesName = "IP 快捷设置" as CFString

func services() -> [Service] {
    guard let prefs = SCPreferencesCreate(nil, preferencesName, nil),
          let set = SCNetworkSetCopyCurrent(prefs),
          let locationID = SCNetworkSetGetSetID(set) as String?,
          let list = SCNetworkSetCopyServices(set) as? [SCNetworkService] else { return [] }
    let store = SCDynamicStoreCreate(nil, preferencesName, nil, nil)
    return list.compactMap { service in
        guard let id = SCNetworkServiceGetServiceID(service) as String?,
              let name = SCNetworkServiceGetName(service) as String?,
              let interface = SCNetworkServiceGetInterface(service),
              let device = SCNetworkInterfaceGetBSDName(interface) as String? else { return nil }
        let proto = SCNetworkServiceCopyProtocol(service, kSCNetworkProtocolTypeIPv4)
        let values = proto.flatMap { SCNetworkProtocolGetConfiguration($0) as? [String: Any] } ?? [:]
        let current = store.flatMap {
            SCDynamicStoreCopyValue($0, "State:/Network/Service/\(id)/IPv4" as CFString) as? [String: Any]
        } ?? [:]
        return Service(locationID: locationID, id: id, name: name, device: device,
                       enabled: SCNetworkServiceGetEnabled(service),
                       ipv4Enabled: proto.map { SCNetworkProtocolGetEnabled($0) } ?? false,
                       config: IPv4Configuration(values: values), current: IPv4Configuration(values: current))
    }
}

enum IPv4WriteError: LocalizedError {
    case authorization(OSStatus)
    case unavailable
    case changed
    case system(String, Int32)
    case uncertain(String)

    var errorDescription: String? {
        switch self {
        case .authorization(let status):
            return "无法取得系统授权（\(status)）。"
        case .unavailable:
            return "当前网络位置或网卡状态已变更。请重新选择网卡。"
        case .changed:
            return "IPv4 配置已变更。请重新打开菜单确认当前设置。"
        case .system(_, let status) where status == Int32(kSCStatusAccessError):
            return "macOS 未授予修改网络设置的权限。"
        case .system(let step, let status):
            return "\(step)失败（\(status)）。"
        case .uncertain(let details):
            return details
        }
    }
}

final class IPv4Writer {
    private let authorization: AuthorizationRef

    init() throws {
        var reference: AuthorizationRef?
        let status = AuthorizationCreate(nil, nil, [], &reference)
        guard status == errAuthorizationSuccess, let reference else { throw IPv4WriteError.authorization(status) }
        authorization = reference
    }

    deinit {
        AuthorizationFree(authorization, [])
    }

    /// Updates only the selected service's IPv4 protocol in the same network location.
    @discardableResult
    func apply(_ desired: IPv4Configuration, to service: Service) throws -> Bool {
        guard desired != service.config else { return false }
        guard let prefs = SCPreferencesCreateWithAuthorization(nil, preferencesName, nil, authorization) else {
            throw IPv4WriteError.system("打开系统网络设置", SCError())
        }
        guard SCPreferencesLock(prefs, false) else {
            throw IPv4WriteError.system("锁定网络设置", SCError())
        }
        defer { SCPreferencesUnlock(prefs) }

        guard let set = SCNetworkSetCopyCurrent(prefs),
              SCNetworkSetGetSetID(set) as String? == service.locationID,
              let members = SCNetworkSetCopyServices(set) as? [SCNetworkService],
              let target = members.first(where: { SCNetworkServiceGetServiceID($0) as String? == service.id }),
              SCNetworkServiceGetEnabled(target),
              let interface = SCNetworkServiceGetInterface(target),
              SCNetworkInterfaceGetBSDName(interface) as String? == service.device,
              let proto = SCNetworkServiceCopyProtocol(target, kSCNetworkProtocolTypeIPv4),
              SCNetworkProtocolGetEnabled(proto) else {
            throw IPv4WriteError.unavailable
        }
        let actual = IPv4Configuration(values: SCNetworkProtocolGetConfiguration(proto) as? [String: Any] ?? [:])
        guard actual == service.config else { throw IPv4WriteError.changed }

        guard stage(desired, for: proto) else {
            throw IPv4WriteError.system("准备 IPv4 配置", SCError())
        }

        let committed = SCPreferencesCommitChanges(prefs)
        let applied = committed && SCPreferencesApplyChanges(prefs)
        let status = SCError()
        // Commit can report failure after writing to disk. Read from a fresh session.
        let saved = readBack(service)
        if applied, saved == desired { return true }

        let step = committed ? "应用 IPv4 配置" : "保存 IPv4 配置"
        if saved == desired {
            if stage(actual, for: proto), SCPreferencesCommitChanges(prefs),
               SCPreferencesApplyChanges(prefs), readBack(service) == actual {
                throw IPv4WriteError.system(step, status)
            }
            throw IPv4WriteError.uncertain("\(step)失败，无法确认已恢复原配置。")
        }
        if !applied, saved == actual { throw IPv4WriteError.system(step, status) }
        throw IPv4WriteError.uncertain("无法核对写入后的系统配置。")
    }

    private func stage(_ configuration: IPv4Configuration, for proto: SCNetworkProtocol) -> Bool {
        let values = configuration.values
        return SCNetworkProtocolSetConfiguration(proto, values.isEmpty ? nil : values as CFDictionary)
    }

    private func readBack(_ service: Service) -> IPv4Configuration? {
        guard let prefs = SCPreferencesCreate(nil, preferencesName, nil),
              let target = SCNetworkServiceCopy(prefs, service.id as CFString),
              let proto = SCNetworkServiceCopyProtocol(target, kSCNetworkProtocolTypeIPv4) else { return nil }
        return IPv4Configuration(values: SCNetworkProtocolGetConfiguration(proto) as? [String: Any] ?? [:])
    }
}
