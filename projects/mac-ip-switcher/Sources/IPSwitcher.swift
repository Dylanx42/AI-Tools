import AppKit
import SystemConfiguration
import Darwin

struct Service {
    let id: String
    let name: String
    let device: String
    let enabled: Bool
    let config: [String: Any]
    let current: [String: Any]
}

struct Preset: Codable {
    var id: String = UUID().uuidString
    var serviceID: String
    var name: String
    var address: String
    var mask: String
    var router: String
}

func services() -> [Service] {
    guard let prefs = SCPreferencesCreate(nil, "IP Switcher" as CFString, nil),
          let set = SCNetworkSetCopyCurrent(prefs),
          let list = SCNetworkSetCopyServices(set) as? [SCNetworkService] else { return [] }
    let store = SCDynamicStoreCreate(nil, "IP Switcher" as CFString, nil, nil)
    return list.compactMap { service in
        guard let id = SCNetworkServiceGetServiceID(service) as String?,
              let name = SCNetworkServiceGetName(service) as String?,
              let interface = SCNetworkServiceGetInterface(service),
              let device = SCNetworkInterfaceGetBSDName(interface) as String? else { return nil }
        let proto = SCNetworkServiceCopyProtocol(service, kSCNetworkProtocolTypeIPv4)
        let config = proto.flatMap { SCNetworkProtocolGetConfiguration($0) as? [String: Any] } ?? [:]
        let current = store.flatMap { SCDynamicStoreCopyValue($0, "State:/Network/Service/\(id)/IPv4" as CFString) as? [String: Any] } ?? [:]
        return Service(id: id, name: name, device: device, enabled: SCNetworkServiceGetEnabled(service), config: config, current: current)
    }
}

func first(_ value: Any?) -> String {
    if let values = value as? [String] { return values.first ?? "" }
    return value as? String ?? ""
}
func validIP(_ value: String) -> Bool {
    var addr = in_addr()
    return value.withCString { inet_pton(AF_INET, $0, &addr) } == 1
}
func validMask(_ value: String) -> Bool {
    guard validIP(value) else { return false }
    let parts = value.split(separator: ".").compactMap { UInt32($0) }
    guard parts.count == 4 else { return false }
    let mask = parts.reduce(UInt32(0)) { ($0 << 8) | $1 }
    let inv = ~mask
    return mask != 0 && (inv &+ 1) & inv == 0
}
func shellQuote(_ s: String) -> String { "'" + s.replacingOccurrences(of: "'", with: "'\\''") + "'" }
func appleQuote(_ s: String) -> String { "\"" + s.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "\"", with: "\\\"").replacingOccurrences(of: "\n", with: "\\n").replacingOccurrences(of: "\r", with: "\\r") + "\"" }

final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    var status: NSStatusItem!
    var presets: [Preset] = []
    let defaultsKey = "savedIPv4Presets"

    func applicationDidFinishLaunching(_ notification: Notification) {
        if let data = UserDefaults.standard.data(forKey: defaultsKey), let saved = try? JSONDecoder().decode([Preset].self, from: data) { presets = saved }
        status = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        status.button?.image = NSImage(systemSymbolName: "network", accessibilityDescription: "IP 快捷设置")
        status.button?.image?.isTemplate = true
        let menu = NSMenu()
        menu.delegate = self
        status.menu = menu
    }
    func savePresets() {
        if let data = try? JSONEncoder().encode(presets) { UserDefaults.standard.set(data, forKey: defaultsKey) }
    }
    func item(_ title: String, _ action: Selector? = nil, _ represented: Any? = nil) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: "")
        item.target = self
        item.representedObject = represented
        return item
    }
    func menuNeedsUpdate(_ menu: NSMenu) {
        menu.removeAllItems()
        let list = services()
        let heading = item("IP 快捷设置")
        heading.isEnabled = false
        menu.addItem(heading)
        if list.isEmpty { let empty = item("未找到当前网络位置中的网卡"); empty.isEnabled = false; menu.addItem(empty) }
        for service in list {
            let root = item("\(service.name)  ·  \(service.device)\(service.enabled ? "" : "（已停用）")")
            let submenu = NSMenu()
            let ip = first(service.current["Addresses"])
            let method = first(service.config["ConfigMethod"])
            let label = item("当前 IPv4：\(ip.isEmpty ? "未连接或无地址" : ip)")
            label.isEnabled = false; submenu.addItem(label)
            let mode = item("配置方式：\(method == "DHCP" ? "DHCP" : method == "Manual" ? "手动" : (method.isEmpty ? "未知" : method))")
            mode.isEnabled = false; submenu.addItem(mode)
            submenu.addItem(.separator())
            let manual = item("设置静态 IPv4…", #selector(editManual(_:)), service.id)
            manual.isEnabled = service.enabled; submenu.addItem(manual)
            let dhcp = item("切换到 DHCP…", #selector(setDHCP(_:)), service.id)
            dhcp.isEnabled = service.enabled; submenu.addItem(dhcp)
            let saved = presets.filter { $0.serviceID == service.id }
            if !saved.isEmpty {
                submenu.addItem(.separator())
                for preset in saved {
                    let p = item("使用：\(preset.name)（\(preset.address)）…", #selector(applyPreset(_:)), preset.id)
                    p.isEnabled = service.enabled; submenu.addItem(p)
                }
                let remove = item("删除已保存配置")
                let removeMenu = NSMenu()
                for preset in saved { removeMenu.addItem(item(preset.name, #selector(deletePreset(_:)), preset.id)) }
                remove.submenu = removeMenu; submenu.addItem(remove)
            }
            root.submenu = submenu; menu.addItem(root)
        }
        menu.addItem(.separator())
        menu.addItem(item("退出 IP 快捷设置", #selector(quit)))
    }
    func findService(_ id: String) -> Service? {
        let all = services()
        guard let service = all.first(where: { $0.id == id }), service.enabled else { message("网卡不可用", "网络服务已移除或停用，请重新打开菜单。 "); return nil }
        guard all.filter({ $0.name == service.name }).count == 1 else { message("网络服务名称重复", "macOS 的网络命令按服务名称操作。请先在系统设置中为网络服务设置唯一名称。 "); return nil }
        return service
    }
    func message(_ title: String, _ info: String) {
        NSApp.activate(ignoringOtherApps: true)
        let alert = NSAlert(); alert.messageText = title; alert.informativeText = info; alert.runModal()
    }
    func confirm(_ title: String, _ info: String) -> Bool {
        NSApp.activate(ignoringOtherApps: true)
        let alert = NSAlert(); alert.messageText = title; alert.informativeText = info
        alert.addButton(withTitle: "继续"); alert.addButton(withTitle: "取消")
        return alert.runModal() == .alertFirstButtonReturn
    }
    func run(_ service: Service, _ args: [String]) -> Bool {
        let cmd = (["/usr/sbin/networksetup"] + args).map(shellQuote).joined(separator: " ")
        let source = "do shell script \(appleQuote(cmd)) with administrator privileges"
        var error: NSDictionary?
        guard let script = NSAppleScript(source: source) else { message("无法执行", "无法创建系统授权请求。"); return false }
        _ = script.executeAndReturnError(&error)
        if let error = error {
            let number = error[NSAppleScript.errorNumber] as? Int
            if number != -128 { message("网络设置未完成", (error[NSAppleScript.errorMessage] as? String) ?? "系统未返回详细错误。") }
            return false
        }
        message("设置已提交", "\(service.name) 的 IPv4 设置已更新。网络可能需要片刻重新连接，请在菜单中刷新查看当前地址。")
        return true
    }
    @objc func setDHCP(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String, let service = findService(id) else { return }
        guard confirm("切换到 DHCP？", "将 \(service.name)（\(service.device)）的 IPv4 改为自动获取。当前连接可能暂时中断。") else { return }
        _ = run(service, ["-setdhcp", service.name])
    }
    @objc func editManual(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String, let service = findService(id) else { return }
        let alert = NSAlert(); alert.messageText = "设置静态 IPv4"; alert.informativeText = "\(service.name)（\(service.device)）\n修改后网络可能暂时中断。"
        alert.addButton(withTitle: "应用"); alert.addButton(withTitle: "取消")
        let view = NSView(frame: NSRect(x: 0, y: 0, width: 320, height: 155))
        func field(_ title: String, _ y: CGFloat, _ value: String) -> NSTextField {
            let label = NSTextField(labelWithString: title); label.frame = NSRect(x: 0, y: y + 3, width: 82, height: 20); view.addSubview(label)
            let text = NSTextField(string: value); text.frame = NSRect(x: 85, y: y, width: 230, height: 24); view.addSubview(text); return text
        }
        let ip = field("IP 地址", 125, first(service.config["Addresses"]).isEmpty ? first(service.current["Addresses"]) : first(service.config["Addresses"]))
        let mask = field("子网掩码", 95, first(service.config["SubnetMasks"]).isEmpty ? first(service.current["SubnetMasks"]) : first(service.config["SubnetMasks"]))
        let router = field("路由器", 65, first(service.config["Router"]).isEmpty ? first(service.current["Router"]) : first(service.config["Router"]))
        let name = field("保存名称", 35, "")
        let tip = NSTextField(labelWithString: "填写保存名称可供以后快捷切换（可选）")
        tip.font = .systemFont(ofSize: 11); tip.textColor = .secondaryLabelColor; tip.frame = NSRect(x: 85, y: 10, width: 230, height: 18); view.addSubview(tip)
        alert.accessoryView = view
        NSApp.activate(ignoringOtherApps: true)
        while alert.runModal() == .alertFirstButtonReturn {
            let addr = ip.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
            let netmask = mask.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
            let gateway = router.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
            let title = name.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
            guard validIP(addr), validMask(netmask), validIP(gateway) else { message("地址格式不正确", "请输入有效的 IPv4 地址、连续的子网掩码和路由器地址。 "); continue }
            guard let latest = findService(id) else { return }
            if run(latest, ["-setmanual", latest.name, addr, netmask, gateway]), !title.isEmpty {
                presets.append(Preset(serviceID: id, name: title, address: addr, mask: netmask, router: gateway)); savePresets()
            }
            return
        }
    }
    @objc func applyPreset(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String, let p = presets.first(where: { $0.id == id }), let service = findService(p.serviceID) else { return }
        guard validIP(p.address), validMask(p.mask), validIP(p.router) else { message("保存的配置无效", "请删除并重新创建该配置。"); return }
        guard confirm("应用“\(p.name)”？", "\(service.name)（\(service.device)）\nIP：\(p.address)\n掩码：\(p.mask)\n路由器：\(p.router)\n\n当前连接可能暂时中断。") else { return }
        _ = run(service, ["-setmanual", service.name, p.address, p.mask, p.router])
    }
    @objc func deletePreset(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String, let p = presets.first(where: { $0.id == id }), confirm("删除“\(p.name)”？", "只删除本地保存的快捷配置，不修改当前网络设置。") else { return }
        presets.removeAll { $0.id == id }; savePresets()
    }
    @objc func quit() { NSApp.terminate(nil) }
}

if CommandLine.arguments.contains("--self-check") {
    precondition(validIP("192.168.1.20") && !validIP("999.1.2.3") && !validIP("1.2.3.4; id"))
    precondition(validMask("255.255.255.0") && validMask("255.255.255.255"))
    precondition(!validMask("255.0.255.0") && !validMask("0.0.0.0"))
    precondition(shellQuote("a'b") == "'a'\\''b'")
    let list = services()
    print("校验通过；当前网络位置发现 \(list.count) 个可显示的网络服务。")
    exit(0)
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
