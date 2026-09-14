import Cocoa

func projectRoot() -> String {
    let env = ProcessInfo.processInfo.environment["WF610_ROOT"]
    if let env, !env.isEmpty { return env }
    let home = FileManager.default.homeDirectoryForCurrentUser
    let local = home.appendingPathComponent("WF610").path
    if FileManager.default.fileExists(atPath: local + "/wf610-ble-open.sh") {
        return local
    }
    let repo = home.appendingPathComponent("Projects/AI-Tools/projects/wf610-ble/scripts").path
    if FileManager.default.fileExists(atPath: repo + "/wf610-ble-open.sh") {
        return repo
    }
    return local
}

let root = projectRoot()
let openScript = root + "/wf610-ble-open.sh"
let stopScript = root + "/wf610-ble-stop.sh"
let stateFile = "/tmp/wf610-ble-bridge.state"
let portFile = "/tmp/ttyWF610BLE"
let bridgePath = root + "/wf610-ble-bridge.py"
let logFile = "/tmp/wf610-ble-menubar.log"

func appendLog(_ text: String) {
    let line = ISO8601DateFormatter().string(from: Date()) + " " + text + "\n"
    if let data = line.data(using: .utf8) {
        if FileManager.default.fileExists(atPath: logFile) {
            if let handle = FileHandle(forWritingAtPath: logFile) {
                handle.seekToEndOfFile()
                handle.write(data)
                handle.closeFile()
            }
        } else {
            FileManager.default.createFile(atPath: logFile, contents: data)
        }
    }
}

func runShell(_ args: [String]) -> (Int32, String) {
    let task = Process()
    task.executableURL = URL(fileURLWithPath: "/usr/bin/env")
    task.arguments = args
    let pipe = Pipe()
    task.standardOutput = pipe
    task.standardError = pipe
    do {
        try task.run()
        task.waitUntilExit()
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        let text = String(data: data, encoding: .utf8) ?? ""
        return (task.terminationStatus, text)
    } catch {
        return (1, String(describing: error))
    }
}

func bridgeRunning() -> Bool {
    let (code, out) = runShell(["pgrep", "-f", bridgePath])
    return code == 0 && !out.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
}

struct BridgeState {
    var name: String = "idle"
    var connectedAt: Date? = nil
}

func readState() -> BridgeState {
    guard let raw = try? String(contentsOfFile: stateFile, encoding: .utf8) else {
        return BridgeState()
    }
    let parts = raw.trimmingCharacters(in: .whitespacesAndNewlines).split(separator: " ", maxSplits: 1).map(String.init)
    guard let name = parts.first, !name.isEmpty else { return BridgeState() }
    var ts: Date? = nil
    if parts.count == 2 {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withDashSeparatorInDate, .withColonSeparatorInTime, .withTimeZone]
        ts = iso.date(from: parts[1])
        if ts == nil {
            let f = DateFormatter()
            f.locale = Locale(identifier: "en_US_POSIX")
            f.dateFormat = "yyyy-MM-dd'T'HH:mm:ssXXXXX"
            ts = f.date(from: parts[1])
        }
    }
    return BridgeState(name: name, connectedAt: ts)
}

func portExists() -> Bool {
    return FileManager.default.fileExists(atPath: portFile)
}

func formatDuration(_ date: Date?) -> String {
    guard let date else { return "—" }
    let secs = max(0, Int(Date().timeIntervalSince(date)))
    let h = secs / 3600
    let m = (secs % 3600) / 60
    let s = secs % 60
    if h > 0 { return "\(h)小时\(m)分" }
    if m > 0 { return "\(m)分\(s)秒" }
    return "\(s)秒"
}

func formatClock(_ date: Date?) -> String {
    guard let date else { return "—" }
    let f = DateFormatter()
    f.dateFormat = "HH:mm:ss"
    return f.string(from: date)
}

class AppDelegate: NSObject, NSApplicationDelegate {
    let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    let statusMenuItem = NSMenuItem(title: "状态：未连接", action: nil, keyEquivalent: "")
    let timeMenuItem = NSMenuItem(title: "连接时间：—", action: nil, keyEquivalent: "")
    let sinceMenuItem = NSMenuItem(title: "已连接：—", action: nil, keyEquivalent: "")
    let connectItem = NSMenuItem(title: "开启连接", action: #selector(connectClicked), keyEquivalent: "")
    let disconnectItem = NSMenuItem(title: "关闭连接", action: #selector(disconnectClicked), keyEquivalent: "")
    var busy = false
    var timer: Timer?

    func applicationDidFinishLaunching(_ notification: Notification) {
        appendLog("native menubar started")
        if let button = statusItem.button {
            button.title = "WF610 · 未连接"
        }
        let menu = NSMenu()
        statusMenuItem.isEnabled = false
        timeMenuItem.isEnabled = false
        sinceMenuItem.isEnabled = false
        connectItem.target = self
        disconnectItem.target = self
        let quitItem = NSMenuItem(title: "退出应用", action: #selector(quitClicked), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(statusMenuItem)
        menu.addItem(timeMenuItem)
        menu.addItem(sinceMenuItem)
        menu.addItem(.separator())
        menu.addItem(connectItem)
        menu.addItem(disconnectItem)
        menu.addItem(.separator())
        menu.addItem(quitItem)
        statusItem.menu = menu
        refresh()
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            self?.refresh()
        }
        if let timer { RunLoop.main.add(timer, forMode: .common) }
    }

    func refresh() {
        let st = readState()
        let running = bridgeRunning()
        let connected = running && portExists() && st.name == "connected"
        if connected {
            statusItem.button?.title = "WF610 · 已连接"
            statusMenuItem.title = "状态：已连接"
            timeMenuItem.title = "连接时间：" + formatClock(st.connectedAt)
            sinceMenuItem.title = "已连接：" + formatDuration(st.connectedAt)
        } else if st.name == "connecting" || (running && ["starting", "scanning", "connecting"].contains(st.name)) {
            statusItem.button?.title = "WF610 · 连接中"
            statusMenuItem.title = "状态：连接中"
            timeMenuItem.title = "连接时间：—"
            sinceMenuItem.title = "已连接：—"
        } else {
            statusItem.button?.title = "WF610 · 未连接"
            statusMenuItem.title = "状态：未连接"
            timeMenuItem.title = "连接时间：—"
            sinceMenuItem.title = "已连接：—"
        }
        connectItem.isEnabled = !busy && !connected
        disconnectItem.isEnabled = !busy && running
    }

    @objc func connectClicked() {
        runScript(openScript, notice: "正在连接 WF610…")
    }

    @objc func disconnectClicked() {
        runScript(stopScript, notice: "正在关闭连接…")
    }

    @objc func quitClicked() {
        NSApp.terminate(nil)
    }

    func runScript(_ path: String, notice: String) {
        if busy { return }
        busy = true
        statusItem.button?.title = "WF610 · 处理中"
        notify(notice)
        DispatchQueue.global(qos: .userInitiated).async {
            let (code, out) = runShell(["/bin/zsh", path])
            appendLog("script \(path) exit=\(code)\n\(out)")
            DispatchQueue.main.async {
                self.busy = false
                let trimmed = out.trimmingCharacters(in: .whitespacesAndNewlines)
                if code == 0 {
                    self.notify(trimmed.split(separator: "\n").last.map(String.init) ?? "完成")
                } else {
                    self.alert("操作失败", trimmed.isEmpty ? "exit \(code)" : trimmed)
                }
                self.refresh()
            }
        }
    }

    func notify(_ text: String) {
        let n = NSUserNotification()
        n.title = "WF610 BLE"
        n.informativeText = text
        NSUserNotificationCenter.default.deliver(n)
    }

    func alert(_ title: String, _ text: String) {
        let a = NSAlert()
        a.messageText = title
        a.informativeText = String(text.suffix(800))
        a.alertStyle = .warning
        a.runModal()
    }
}


@main
enum AppMain {
    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.setActivationPolicy(.accessory)
        app.run()
    }
}
