import AppKit
import Carbon

struct Preset: Codable {
    var id: String = UUID().uuidString
    var serviceID: String
    var name: String
    var address: String
    var mask: String
    var router: String
}

final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    var status: NSStatusItem!
    var presets: [Preset] = []
    let defaultsKey = "savedIPv4Presets"
    let recoveryKey = "previousIPv4Configurations"
    let visibilityKey = "visibleNetworkServices"
    let shortcutKey = "globalShortcutChoice"
    var hotKey: EventHotKeyRef?
    var hotKeyHandler: EventHandlerRef?
    var hotKeyAvailable = false
    let shortcuts: [(String, UInt32)] = [("⌃⌥⌘ I", UInt32(kVK_ANSI_I)), ("⌃⌥⌘ J", UInt32(kVK_ANSI_J)), ("⌃⌥⌘ K", UInt32(kVK_ANSI_K))]

    func preferred(_ service: Service) -> Bool {
        if let ids = UserDefaults.standard.stringArray(forKey: visibilityKey) { return ids.contains(service.id) }
        return service.name == "Wi-Fi" || service.name == "USB 10/100/1000 LAN"
    }
    var shortcutChoice: Int {
        UserDefaults.standard.object(forKey: shortcutKey) == nil ? 0 : UserDefaults.standard.integer(forKey: shortcutKey)
    }
    func installHotKey(_ choice: Int) -> Bool {
        guard shortcuts.indices.contains(choice) else { return choice == -1 }
        var ref: EventHotKeyRef?
        let id = EventHotKeyID(signature: OSType(0x49505357), id: 1)
        let modifiers = UInt32(controlKey | optionKey | cmdKey)
        let result = RegisterEventHotKey(shortcuts[choice].1, modifiers, id, GetApplicationEventTarget(), OptionBits(kEventHotKeyExclusive), &ref)
        guard result == noErr, let ref = ref else { return false }
        hotKey = ref
        return true
    }
    func configureHotKey() {
        var type = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        InstallEventHandler(GetApplicationEventTarget(), { _, event, context in
            guard let event = event, let context = context else { return OSStatus(eventNotHandledErr) }
            var id = EventHotKeyID()
            guard GetEventParameter(event, EventParamName(kEventParamDirectObject), EventParamType(typeEventHotKeyID), nil, MemoryLayout<EventHotKeyID>.size, nil, &id) == noErr,
                  id.signature == OSType(0x49505357), id.id == 1 else { return OSStatus(eventNotHandledErr) }
            let delegate = Unmanaged<AppDelegate>.fromOpaque(context).takeUnretainedValue()
            DispatchQueue.main.async { delegate.status.button?.performClick(nil) }
            return noErr
        }, 1, &type, Unmanaged.passUnretained(self).toOpaque(), &hotKeyHandler)
        hotKeyAvailable = installHotKey(shortcutChoice)
    }
    @objc func chooseShortcut(_ sender: NSMenuItem) {
        guard let choice = sender.representedObject as? Int, choice != shortcutChoice || !hotKeyAvailable else { return }
        let old = shortcutChoice
        if let ref = hotKey { UnregisterEventHotKey(ref); hotKey = nil }
        if installHotKey(choice) {
            UserDefaults.standard.set(choice, forKey: shortcutKey)
            hotKeyAvailable = true
        } else {
            hotKeyAvailable = installHotKey(old)
            message("快捷键不可用", "该组合已被系统或其他程序占用，请选择其他组合。原设置保持不变。")
        }
    }
    @objc func toggleService(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String else { return }
        let all = services()
        var ids = Set(UserDefaults.standard.stringArray(forKey: visibilityKey) ?? all.filter { preferred($0) }.map { $0.id })
        if ids.contains(id) { ids.remove(id) } else { ids.insert(id) }
        UserDefaults.standard.set(Array(ids), forKey: visibilityKey)
    }


    func applicationDidFinishLaunching(_ notification: Notification) {
        if let data = UserDefaults.standard.data(forKey: defaultsKey), let saved = try? JSONDecoder().decode([Preset].self, from: data) { presets = saved }
        status = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        status.button?.image = NSImage(systemSymbolName: "network", accessibilityDescription: "IP 快捷设置")
        status.button?.image?.isTemplate = true
        status.button?.toolTip = "IP 快捷设置"
        let menu = NSMenu()
        menu.delegate = self
        status.menu = menu
        configureHotKey()
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
        let visible = list.filter { preferred($0) }
        let hidden = list.filter { !preferred($0) }
        if visible.isEmpty && !list.isEmpty {
            let empty = item("没有已显示的网卡，请在显示设置中选择")
            empty.isEnabled = false; menu.addItem(empty)
        }
        for service in visible { menu.addItem(serviceItem(service)) }
        if !hidden.isEmpty {
            let other = item("其他网卡（\(hidden.count)）")
            let sub = NSMenu()
            for service in hidden { sub.addItem(serviceItem(service)) }
            other.submenu = sub; menu.addItem(other)
        }
        menu.addItem(.separator())
        let visibility = item("选择显示的网卡")
        let visibilityMenu = NSMenu()
        for service in list {
            let entry = item("\(service.name)  ·  \(service.device)", #selector(toggleService(_:)), service.id)
            entry.state = preferred(service) ? .on : .off
            visibilityMenu.addItem(entry)
        }
        visibility.submenu = visibilityMenu; menu.addItem(visibility)
        let shortcutsItem = item("全局快捷键")
        let shortcutMenu = NSMenu()
        for (index, shortcut) in shortcuts.enumerated() {
            let entry = item(shortcut.0, #selector(chooseShortcut(_:)), index)
            entry.state = shortcutChoice == index && hotKeyAvailable ? .on : .off
            shortcutMenu.addItem(entry)
        }
        let off = item("关闭快捷键", #selector(chooseShortcut(_:)), -1)
        off.state = shortcutChoice == -1 ? .on : .off
        shortcutMenu.addItem(.separator()); shortcutMenu.addItem(off)
        if !hotKeyAvailable {
            let unavailable = item("当前快捷键不可用，请选择其他组合")
            unavailable.isEnabled = false; shortcutMenu.addItem(unavailable)
        }
        shortcutsItem.submenu = shortcutMenu; menu.addItem(shortcutsItem)
        menu.addItem(.separator())
        menu.addItem(item("退出 IP 快捷设置", #selector(quit)))
    }
    func serviceItem(_ service: Service) -> NSMenuItem {
        let address = service.current.address
        let configured = service.config.address
        let offline = configured.isEmpty ? "无 IPv4" : "未连接 · 已配置 \(configured)"
        let state = !service.enabled ? "已停用" : (address.isEmpty ? offline : address)
        let root = item("\(service.name)  ·  \(service.device)  ·  \(state)")
        let submenu = NSMenu()
        submenu.autoenablesItems = false
        func addDetail(_ text: String) {
            let detail = item(text)
            detail.isEnabled = false
            submenu.addItem(detail)
        }
        func addAction(_ title: String, _ action: Selector, id: String) {
            let entry = item(title, action, id)
            entry.isEnabled = service.canConfigure
            submenu.addItem(entry)
        }
        addDetail("当前 IPv4：\(address.isEmpty ? "未连接或无地址" : address)")
        addDetail("配置方式：\(service.config.modeLabel)")
        if service.config.isManual {
            addDetail("网关：\(service.config.router.isEmpty ? "无" : service.config.router)")
        }
        submenu.addItem(.separator())
        addAction("设置静态 IPv4…", #selector(editManual(_:)), id: service.id)
        addAction("切换到 DHCP…", #selector(setDHCP(_:)), id: service.id)
        if let previous = previousConfiguration(for: service), previous != service.config {
            addAction("恢复上一次 IPv4 配置…", #selector(restorePrevious(_:)), id: service.id)
        }
        let saved = presets.filter { $0.serviceID == service.id }
        if !saved.isEmpty {
            submenu.addItem(.separator())
            for preset in saved {
                addAction("使用：\(preset.name)（\(preset.address)）…", #selector(applyPreset(_:)), id: preset.id)
            }
            let remove = item("删除已保存配置")
            let removeMenu = NSMenu()
            for preset in saved { removeMenu.addItem(item(preset.name, #selector(deletePreset(_:)), preset.id)) }
            remove.submenu = removeMenu
            submenu.addItem(remove)
        }
        root.submenu = submenu
        return root
    }

    func findService(_ id: String) -> Service? {
        guard let service = services().first(where: { $0.id == id }), service.canConfigure else {
            message("网卡不可用", "网络服务已移除、停用或不支持修改 IPv4。请重新打开菜单。")
            return nil
        }
        return service
    }

    func previousConfiguration(for service: Service) -> IPv4Configuration? {
        guard let values = UserDefaults.standard.dictionary(forKey: recoveryKey)?[service.recoveryKey] as? [String: Any]
        else { return nil }
        return IPv4Configuration(values: values)
    }

    func rememberConfiguration(of service: Service) {
        var records = UserDefaults.standard.dictionary(forKey: recoveryKey) ?? [:]
        records[service.recoveryKey] = service.config.values
        UserDefaults.standard.set(records, forKey: recoveryKey)
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
    func apply(_ configuration: IPv4Configuration, to service: Service) -> Bool {
        do {
            let writer = try IPv4Writer()
            if try writer.apply(configuration, to: service) {
                rememberConfiguration(of: service)
                message("IPv4 设置已保存", "\(service.name) 的新配置已保存并提交给 macOS。请在菜单中查看当前地址。")
            }
            return true
        } catch IPv4WriteError.uncertain(let details) {
            rememberConfiguration(of: service)
            message("请核对 IPv4 设置", "\(details) 你可以在菜单中恢复原配置。")
        } catch {
            message("网络设置未完成", error.localizedDescription)
        }
        return false
    }

    @objc func setDHCP(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String, let service = findService(id) else { return }
        guard confirm("切换到 DHCP？", "将 \(service.name)（\(service.device)）的 IPv4 改为自动获取。当前连接可能暂时中断。") else { return }
        _ = apply(service.config.settingDHCP(), to: service)
    }

    @objc func restorePrevious(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String, let service = findService(id),
              let previous = previousConfiguration(for: service), previous != service.config else { return }
        var summary = "\(service.name)（\(service.device)）\n配置方式：\(previous.modeLabel)"
        if !previous.address.isEmpty {
            summary += "\nIP：\(previous.address)\n掩码：\(previous.mask)"
        }
        if previous.isManual {
            summary += "\n网关：\(previous.router.isEmpty ? "无" : previous.router)"
        }
        guard confirm("恢复上一次 IPv4 配置？", summary) else { return }
        _ = apply(previous, to: service)
    }

    @objc func editManual(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String, let service = findService(id) else { return }
        let alert = NSAlert(); alert.messageText = "设置静态 IPv4"; alert.informativeText = "\(service.name)（\(service.device)）\n修改后网络可能暂时中断。"
        alert.addButton(withTitle: "应用"); alert.addButton(withTitle: "取消")
        let view = NSView(frame: NSRect(x: 0, y: 0, width: 344, height: 151))
        func field(_ title: String, _ y: CGFloat, _ value: String, placeholder: String? = nil) -> NSTextField {
            let label = NSTextField(labelWithString: title)
            label.frame = NSRect(x: 0, y: y + 3, width: 108, height: 20)
            view.addSubview(label)
            let text = NSTextField(string: value)
            text.placeholderString = placeholder
            text.setAccessibilityLabel(title)
            text.frame = NSRect(x: 110, y: y, width: 230, height: 24)
            view.addSubview(text)
            return text
        }
        let initial = service.config.isManual ? service.config : service.current
        let ip = field("IP 地址", 121, initial.address)
        let mask = field("子网掩码", 90, initial.mask)
        let router = field("网关（可选）", 59, service.config.isManual ? service.config.router : "",
                           placeholder: "留空则不设置网关")
        let name = field("保存名称", 28, "", placeholder: "可选，用于下次快速切换")
        ip.nextKeyView = mask
        mask.nextKeyView = router
        router.nextKeyView = name
        alert.accessoryView = view
        alert.window.initialFirstResponder = ip
        NSApp.activate(ignoringOtherApps: true)
        while alert.runModal() == .alertFirstButtonReturn {
            guard let settings = ManualIPv4(address: ip.stringValue, mask: mask.stringValue, gateway: router.stringValue)
            else {
                message("地址格式不正确", "请填写有效的 IPv4 地址和连续的子网掩码。网关可以留空，填写时须为 IPv4 地址。")
                continue
            }
            let title = name.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
            if apply(service.config.settingManual(settings), to: service), !title.isEmpty {
                presets.append(Preset(serviceID: id, name: title, address: settings.address,
                                      mask: settings.mask, router: settings.gateway ?? ""))
                savePresets()
            }
            return
        }
    }

    @objc func applyPreset(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String, let preset = presets.first(where: { $0.id == id }),
              let service = findService(preset.serviceID) else { return }
        guard let settings = ManualIPv4(address: preset.address, mask: preset.mask, gateway: preset.router) else {
            message("保存的配置无效", "请删除并重新创建该配置。")
            return
        }
        let summary = "\(service.name)（\(service.device)）\nIP：\(settings.address)\n掩码：\(settings.mask)\n网关：\(settings.gateway ?? "无")"
        guard confirm("应用“\(preset.name)”？", summary) else { return }
        _ = apply(service.config.settingManual(settings), to: service)
    }

    @objc func deletePreset(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String, let p = presets.first(where: { $0.id == id }), confirm("删除“\(p.name)”？", "只删除本地保存的快捷配置，不修改当前网络设置。") else { return }
        presets.removeAll { $0.id == id }; savePresets()
    }
    @objc func quit() { NSApp.terminate(nil) }
}

func selfCheck() {
    precondition(validIP("192.168.1.20") && !validIP("999.1.2.3") && !validIP("192.168.1.20\0"))
    precondition(validMask("255.255.255.0") && validMask("255.255.255.255"))
    precondition(!validMask("255.0.255.0") && !validMask("0.0.0.0"))
    let existing = IPv4Configuration(values: ["ConfigMethod": "Manual",
                                              "Addresses": ["192.0.2.20"], "SubnetMasks": ["255.255.255.0"],
                                              "Router": "192.0.2.1", "DHCPClientID": "example"])
    let noGateway = ManualIPv4(address: "192.0.2.20", mask: "255.255.255.0", gateway: "  ")!
    let changed = existing.settingManual(noGateway)
    precondition(changed.isManual && changed.values["Router"] == nil)
    precondition(changed.settingDHCP().values["DHCPClientID"] as? String == "example")
    precondition(changed.settingDHCP().settingManual(noGateway) == changed)
    precondition(ManualIPv4(address: "192.0.2.20", mask: "255.255.255.0", gateway: "invalid") == nil)
    print("校验通过；当前网络位置发现 \(services().count) 个网络服务。")
}

@main
enum IPSwitcher {
    @MainActor
    static func main() {
        if CommandLine.arguments.contains("--self-check") {
            selfCheck()
            return
        }
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.setActivationPolicy(.accessory)
        app.run()
    }
}
