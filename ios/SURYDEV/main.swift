import UIKit
import WebKit
import Network
import Security
import CryptoKit

@main
final class SuryadevAppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let w = UIWindow(frame: UIScreen.main.bounds)
        w.rootViewController = SuryadevViewController()
        w.makeKeyAndVisible()
        window = w
        return true
    }
}

final class SecureValueStore {
    private static let service = "com.krishna.suryadev.shravana"
    static func read(_ key: String) -> String? {
        let q: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
    static func write(_ value: String, key: String) {
        let q: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
        ]
        SecItemDelete(q as CFDictionary)
        let add: [String: Any] = q.merging([
            kSecValueData as String: Data(value.utf8),
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]) { _, new in new }
        SecItemAdd(add as CFDictionary, nil)
    }
}

final class SuryadevCoreClient {
    let deviceID: String
    let credential: String
    private let defaults = UserDefaults.standard

    var baseURL: String {
        get { defaults.string(forKey: "suryadev.core.url") ?? "" }
        set {
            let v = newValue.trimmingCharacters(in: .whitespacesAndNewlines)
                .replacingOccurrences(of: "/+$", with: "", options: .regularExpression)
            defaults.set(v, forKey: "suryadev.core.url")
        }
    }

    init() {
        if let x = SecureValueStore.read("device-id") {
            deviceID = x
        } else {
            let x = "suryadev-ipad-" + UUID().uuidString.lowercased()
            SecureValueStore.write(x, key: "device-id")
            deviceID = x
        }
        if let x = SecureValueStore.read("device-credential") {
            credential = x
        } else {
            let x = UUID().uuidString + "-" + UUID().uuidString + "-" + UUID().uuidString
            SecureValueStore.write(x, key: "device-credential")
            credential = x
        }
    }

    var configured: Bool {
        guard let u = URL(string: baseURL), let host = u.host?.lowercased(),
              u.scheme == "http" || u.scheme == "https" else { return false }
        if host == "localhost" || host.hasSuffix(".local") || host.hasSuffix(".ts.net") { return true }
        let p = host.split(separator: ".").compactMap { Int($0) }
        if p.count == 4 && p.allSatisfy({ (0...255).contains($0) }) {
            if p[0] == 10 || (p[0] == 192 && p[1] == 168) { return true }
            if p[0] == 172 && (16...31).contains(p[1]) { return true }
            if p[0] == 100 && (64...127).contains(p[1]) { return true }
        }
        return false
    }

    private func request(_ path: String, method: String = "POST", body: [String: Any]? = nil,
                         authenticated: Bool = true,
                         completion: @escaping (Int, [String: Any]?) -> Void) {
        guard configured, let url = URL(string: baseURL + path) else {
            completion(0, ["error": "trusted KRISHNA private URL is not configured"])
            return
        }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.timeoutInterval = 12
        req.cachePolicy = .reloadIgnoringLocalCacheData
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if authenticated {
            req.setValue(deviceID, forHTTPHeaderField: "X-Krishna-Device")
            req.setValue("Device " + credential, forHTTPHeaderField: "Authorization")
        }
        if let body {
            req.httpBody = try? JSONSerialization.data(withJSONObject: body)
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        URLSession.shared.dataTask(with: req) { data, response, _ in
            let code = (response as? HTTPURLResponse)?.statusCode ?? 0
            var obj: [String: Any]?
            if let data, let parsed = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                obj = parsed
            }
            completion(code, obj)
        }.resume()
    }

    func requestPairing(_ completion: @escaping (Int, [String: Any]?) -> Void) {
        let hash = SHA256.hash(data: Data(credential.utf8)).map { String(format: "%02x", $0) }.joined()
        request("/api/mobile/pair/request", body: [
            "device_id": deviceID,
            "name": "SURYADEV SHRAVANA iPad",
            "credential_sha256": hash,
        ], authenticated: false, completion: completion)
    }

    func bootstrap(_ completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/mobile/bootstrap", method: "GET", authenticated: true, completion: completion)
    }
    func queue(_ completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/suryadev/podcast/queue", method: "GET", authenticated: true, completion: completion)
    }
    func status(_ completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/suryadev/device/status?device_id=" + deviceID.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed)!,
                method: "GET", authenticated: true, completion: completion)
    }
    func heartbeat(_ body: [String: Any], completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/suryadev/device/heartbeat", body: body, completion: completion)
    }
    func alert(_ body: [String: Any], completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/suryadev/device/alert", body: body, completion: completion)
    }
    func learning(_ body: [String: Any], completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/suryadev/device/learning", body: body, completion: completion)
    }
    func research(_ query: String, completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/suryadev/device/research", body: [
            "device_id": deviceID, "query": query, "limit": 8,
        ], completion: completion)
    }
}

final class StatusLamp: UIView {
    private let dot = UIView()
    private let label = UILabel()
    init(_ title: String) {
        super.init(frame: .zero)
        translatesAutoresizingMaskIntoConstraints = false
        dot.translatesAutoresizingMaskIntoConstraints = false
        dot.layer.cornerRadius = 5
        label.translatesAutoresizingMaskIntoConstraints = false
        label.text = title
        label.font = .monospacedSystemFont(ofSize: 10, weight: .semibold)
        label.textColor = UIColor.white.withAlphaComponent(0.88)
        addSubview(dot); addSubview(label)
        NSLayoutConstraint.activate([
            dot.leadingAnchor.constraint(equalTo: leadingAnchor),
            dot.centerYAnchor.constraint(equalTo: centerYAnchor),
            dot.widthAnchor.constraint(equalToConstant: 10),
            dot.heightAnchor.constraint(equalToConstant: 10),
            label.leadingAnchor.constraint(equalTo: dot.trailingAnchor, constant: 5),
            label.trailingAnchor.constraint(equalTo: trailingAnchor),
            label.topAnchor.constraint(equalTo: topAnchor),
            label.bottomAnchor.constraint(equalTo: bottomAnchor),
        ])
        set(false)
    }
    required init?(coder: NSCoder) { fatalError() }
    func set(_ green: Bool) {
        dot.backgroundColor = green ? UIColor.systemGreen : UIColor.systemRed
        dot.layer.shadowColor = dot.backgroundColor?.cgColor
        dot.layer.shadowOpacity = 0.8
        dot.layer.shadowRadius = 5
        dot.layer.shadowOffset = .zero
    }
}

struct PodcastQueueItem {
    let rank: Int
    let show: String
    let youtubeURL: String
    let youtubeSearch: String
}

final class PodcastQueueViewController: UIViewController, UITableViewDataSource, UITableViewDelegate {
    let items: [PodcastQueueItem]
    let onSelect: (PodcastQueueItem) -> Void
    let table = UITableView(frame: .zero, style: .insetGrouped)
    init(items: [PodcastQueueItem], onSelect: @escaping (PodcastQueueItem) -> Void) {
        self.items = items; self.onSelect = onSelect
        super.init(nibName: nil, bundle: nil)
        modalPresentationStyle = .formSheet
    }
    required init?(coder: NSCoder) { fatalError() }
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        title = "Top 30 Podcast Queue"
        table.translatesAutoresizingMaskIntoConstraints = false
        table.dataSource = self; table.delegate = self
        view.addSubview(table)
        let close = UIButton(type: .system)
        close.setTitle("Close", for: .normal)
        close.translatesAutoresizingMaskIntoConstraints = false
        close.addTarget(self, action: #selector(done), for: .touchUpInside)
        view.addSubview(close)
        NSLayoutConstraint.activate([
            close.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 8),
            close.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -16),
            table.topAnchor.constraint(equalTo: close.bottomAnchor, constant: 8),
            table.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            table.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            table.bottomAnchor.constraint(equalTo: view.bottomAnchor),
        ])
    }
    @objc private func done() { dismiss(animated: true) }
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { items.count }
    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let c = UITableViewCell(style: .subtitle, reuseIdentifier: nil)
        let item = items[indexPath.row]
        c.textLabel?.text = "\(item.rank). \(item.show)"
        c.detailTextLabel?.text = "Tap to open podcast-only YouTube search"
        c.accessoryType = .disclosureIndicator
        return c
    }
    func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        onSelect(items[indexPath.row]); dismiss(animated: true)
    }
}

final class ResearchViewController: UIViewController {
    private let client: SuryadevCoreClient
    private let field = UITextField()
    private let output = UITextView()

    init(client: SuryadevCoreClient) {
        self.client = client
        super.init(nibName: nil, bundle: nil)
        modalPresentationStyle = .formSheet
    }
    required init?(coder: NSCoder) { fatalError() }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        let titleLabel = UILabel()
        titleLabel.translatesAutoresizingMaskIntoConstraints = false
        titleLabel.text = "GARUDANETRA WEB · SHRAVANA"
        titleLabel.font = .systemFont(ofSize: 18, weight: .bold)

        field.translatesAutoresizingMaskIntoConstraints = false
        field.placeholder = "Research a podcast claim, guest, topic, paper, company…"
        field.borderStyle = .roundedRect
        field.autocapitalizationType = .sentences
        field.returnKeyType = .search

        let search = UIButton(type: .system)
        search.translatesAutoresizingMaskIntoConstraints = false
        search.setTitle("Research", for: .normal)
        search.addTarget(self, action: #selector(runResearch), for: .touchUpInside)

        let close = UIButton(type: .system)
        close.translatesAutoresizingMaskIntoConstraints = false
        close.setTitle("Close", for: .normal)
        close.addTarget(self, action: #selector(done), for: .touchUpInside)

        output.translatesAutoresizingMaskIntoConstraints = false
        output.isEditable = false
        output.font = .monospacedSystemFont(ofSize: 12, weight: .regular)
        output.text = "Garudanetra runs on KRISHNA PC. Results here are verification evidence, not automatically accepted knowledge."

        view.addSubview(titleLabel); view.addSubview(field); view.addSubview(search); view.addSubview(close); view.addSubview(output)
        NSLayoutConstraint.activate([
            titleLabel.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 18),
            titleLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            close.centerYAnchor.constraint(equalTo: titleLabel.centerYAnchor),
            close.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            field.topAnchor.constraint(equalTo: titleLabel.bottomAnchor, constant: 16),
            field.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            search.leadingAnchor.constraint(equalTo: field.trailingAnchor, constant: 10),
            search.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            search.centerYAnchor.constraint(equalTo: field.centerYAnchor),
            search.widthAnchor.constraint(equalToConstant: 90),
            output.topAnchor.constraint(equalTo: field.bottomAnchor, constant: 14),
            output.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            output.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            output.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -16),
        ])
    }

    @objc private func done() { dismiss(animated: true) }

    @objc private func runResearch() {
        let q = field.text?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !q.isEmpty else { return }
        output.text = "GARUDANETRA · researching…"
        client.research(q) { [weak self] code, obj in
            DispatchQueue.main.async {
                guard let self else { return }
                guard (200..<300).contains(code), let obj else {
                    self.output.text = "Research failed or KRISHNA PC is unavailable."
                    return
                }
                let report = obj["report"] as? [String: Any] ?? [:]
                let web = report["web"] as? [[String: Any]] ?? []
                var lines = ["QUERY: \(q)", ""]
                for (i,row) in web.prefix(8).enumerated() {
                    lines.append("\(i+1). \(row["title"] as? String ?? "Result")")
                    if let u = row["url"] as? String { lines.append(u) }
                    if let s = row["summary"] as? String { lines.append(String(s.prefix(500))) }
                    lines.append("")
                }
                if web.isEmpty { lines.append("No web evidence returned.") }
                lines.append("Evidence remains candidate until Rishi/BRAHMA verification.")
                self.output.text = lines.joined(separator: "\n")
            }
        }
    }
}

final class SuryadevViewController: UIViewController, WKNavigationDelegate, WKUIDelegate {
    private let client = SuryadevCoreClient()
    private let pathMonitor = NWPathMonitor()
    private let networkQueue = DispatchQueue(label: "suryadev.shravana.network")
    private var web: WKWebView!

    private let nodeIDLabel = UILabel()
    private let batteryLabel = UILabel()
    private let queueLabel = UILabel()
    private let selectedLabel = UILabel()
    private let linkLamp = StatusLamp("KRISHNA LINK")
    private let workLamp = StatusLamp("SURYADEV WORKING")
    private let learningLamp = StatusLamp("RISHI LEARNING")

    private var queueItems: [PodcastQueueItem] = []
    private var selectedShow = ""
    private var networkUp = false
    private var lastNetworkUp: Bool?
    private var heartbeatFailures = 0
    private var healthTimer: Timer?
    private var sampleTimer: Timer?
    private var learningTimer: Timer?
    private var learningBuffer: [String] = []
    private var learningStart: Double = 0
    private var latestVideoTime: Double = 0
    private var latestPaused = true
    private var latestTitle = ""
    private var latestURL = ""
    private var lastLearningAcceptedAt: Date?
    private var lastLearningFlush = Date()
    private var battery50Sent = false
    private var battery20Sent = false
    private var lastThermal = ProcessInfo.ThermalState.nominal
    private var pendingAlerts: [[String: Any]] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 0.008, green: 0.025, blue: 0.045, alpha: 1)
        setupWeb()
        setupUI()
        UIDevice.current.isBatteryMonitoringEnabled = true
        restoreAlerts()
        registerObservers()
        startNetworkMonitor()
        startTimers()
        forceScreenAwake()
        checkPairingAndQueue()
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        forceScreenAwake()
    }

    deinit {
        healthTimer?.invalidate(); sampleTimer?.invalidate(); learningTimer?.invalidate()
        pathMonitor.cancel()
        NotificationCenter.default.removeObserver(self)
        UIApplication.shared.isIdleTimerDisabled = false
    }

    private func setupWeb() {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.allowsAirPlayForMediaPlayback = true
        config.allowsPictureInPictureMediaPlayback = false
        config.mediaTypesRequiringUserActionForPlayback = []
        config.websiteDataStore = .default()
        web = WKWebView(frame: .zero, configuration: config)
        web.translatesAutoresizingMaskIntoConstraints = false
        web.navigationDelegate = self
        web.uiDelegate = self
        web.allowsBackForwardNavigationGestures = true
        web.backgroundColor = .black
    }

    private func setupUI() {
        let header = UIView()
        header.translatesAutoresizingMaskIntoConstraints = false
        header.backgroundColor = UIColor(red: 0.015, green: 0.085, blue: 0.12, alpha: 0.98)

        let brand = UILabel()
        brand.translatesAutoresizingMaskIntoConstraints = false
        brand.text = "☀︎ SURYADEV SHRAVANA · PODCAST GURUKUL"
        brand.font = .systemFont(ofSize: 14, weight: .bold)
        brand.textColor = UIColor(red: 1.0, green: 0.80, blue: 0.33, alpha: 1)

        nodeIDLabel.translatesAutoresizingMaskIntoConstraints = false
        nodeIDLabel.text = "NODE ID · " + client.deviceID
        nodeIDLabel.font = .monospacedSystemFont(ofSize: 8.5, weight: .medium)
        nodeIDLabel.textColor = UIColor.systemTeal
        nodeIDLabel.numberOfLines = 1
        nodeIDLabel.adjustsFontSizeToFitWidth = true
        nodeIDLabel.minimumScaleFactor = 0.65

        batteryLabel.translatesAutoresizingMaskIntoConstraints = false
        batteryLabel.font = .monospacedSystemFont(ofSize: 10, weight: .bold)
        batteryLabel.textColor = .white
        batteryLabel.text = "BAT --%"

        queueLabel.translatesAutoresizingMaskIntoConstraints = false
        queueLabel.font = .monospacedSystemFont(ofSize: 9, weight: .semibold)
        queueLabel.textColor = UIColor.white.withAlphaComponent(0.76)
        queueLabel.text = "QUEUE 0/30"

        let lamps = UIStackView(arrangedSubviews: [linkLamp, workLamp, learningLamp])
        lamps.translatesAutoresizingMaskIntoConstraints = false
        lamps.axis = .horizontal
        lamps.spacing = 14
        lamps.alignment = .center

        let controls = UIStackView(arrangedSubviews: [
            actionButton("PODCASTS", #selector(showQueue)),
            actionButton("WHAT I LEARNED", #selector(showLearning)),
            actionButton("GARUDANETRA WEB", #selector(showResearch)),
            actionButton("↻", #selector(reload)),
            actionButton("CORE", #selector(configureCore)),
        ])
        controls.translatesAutoresizingMaskIntoConstraints = false
        controls.axis = .horizontal
        controls.spacing = 7
        controls.alignment = .center

        selectedLabel.translatesAutoresizingMaskIntoConstraints = false
        selectedLabel.font = .systemFont(ofSize: 10, weight: .semibold)
        selectedLabel.textColor = UIColor.white.withAlphaComponent(0.9)
        selectedLabel.text = "PODCAST · choose from Top 30 queue"
        selectedLabel.numberOfLines = 1

        view.addSubview(header); header.addSubview(brand); header.addSubview(nodeIDLabel)
        header.addSubview(lamps); header.addSubview(batteryLabel); header.addSubview(queueLabel); header.addSubview(controls)
        view.addSubview(selectedLabel); view.addSubview(web)

        NSLayoutConstraint.activate([
            header.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            header.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            header.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            header.heightAnchor.constraint(equalToConstant: 78),

            brand.leadingAnchor.constraint(equalTo: header.leadingAnchor, constant: 12),
            brand.topAnchor.constraint(equalTo: header.topAnchor, constant: 8),
            nodeIDLabel.leadingAnchor.constraint(equalTo: brand.leadingAnchor),
            nodeIDLabel.topAnchor.constraint(equalTo: brand.bottomAnchor, constant: 5),
            nodeIDLabel.widthAnchor.constraint(lessThanOrEqualTo: header.widthAnchor, multiplier: 0.52),

            lamps.leadingAnchor.constraint(equalTo: brand.trailingAnchor, constant: 18),
            lamps.topAnchor.constraint(equalTo: header.topAnchor, constant: 9),

            batteryLabel.leadingAnchor.constraint(equalTo: lamps.trailingAnchor, constant: 14),
            batteryLabel.centerYAnchor.constraint(equalTo: lamps.centerYAnchor),
            queueLabel.leadingAnchor.constraint(equalTo: batteryLabel.trailingAnchor, constant: 12),
            queueLabel.centerYAnchor.constraint(equalTo: lamps.centerYAnchor),

            controls.trailingAnchor.constraint(equalTo: header.trailingAnchor, constant: -10),
            controls.bottomAnchor.constraint(equalTo: header.bottomAnchor, constant: -7),

            selectedLabel.topAnchor.constraint(equalTo: header.bottomAnchor),
            selectedLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 10),
            selectedLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -10),
            selectedLabel.heightAnchor.constraint(equalToConstant: 28),

            web.topAnchor.constraint(equalTo: selectedLabel.bottomAnchor),
            web.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            web.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            web.bottomAnchor.constraint(equalTo: view.bottomAnchor),
        ])
    }

    private func actionButton(_ title: String, _ action: Selector) -> UIButton {
        let b = UIButton(type: .system)
        b.setTitle(title, for: .normal)
        b.setTitleColor(.white, for: .normal)
        b.titleLabel?.font = .systemFont(ofSize: 10, weight: .bold)
        b.backgroundColor = UIColor.white.withAlphaComponent(0.09)
        b.layer.cornerRadius = 7
        b.heightAnchor.constraint(equalToConstant: 29).isActive = true
        b.contentEdgeInsets = UIEdgeInsets(top: 4, left: 9, bottom: 4, right: 9)
        b.addTarget(self, action: action, for: .touchUpInside)
        return b
    }

    private func forceScreenAwake() {
        UIApplication.shared.isIdleTimerDisabled = true
    }

    private func registerObservers() {
        let n = NotificationCenter.default
        n.addObserver(self, selector: #selector(batteryChanged), name: UIDevice.batteryLevelDidChangeNotification, object: nil)
        n.addObserver(self, selector: #selector(thermalChanged), name: ProcessInfo.thermalStateDidChangeNotification, object: nil)
        n.addObserver(self, selector: #selector(powerChanged), name: .NSProcessInfoPowerStateDidChange, object: nil)
        n.addObserver(self, selector: #selector(memoryWarning), name: UIApplication.didReceiveMemoryWarningNotification, object: nil)
        n.addObserver(self, selector: #selector(appActive), name: UIApplication.didBecomeActiveNotification, object: nil)
        n.addObserver(self, selector: #selector(appInactive), name: UIApplication.willResignActiveNotification, object: nil)
    }

    private func startNetworkMonitor() {
        pathMonitor.pathUpdateHandler = { [weak self] path in
            guard let self else { return }
            let up = path.status == .satisfied
            DispatchQueue.main.async {
                let prior = self.lastNetworkUp
                self.networkUp = up; self.lastNetworkUp = up
                if let prior, prior != up {
                    self.queueAlert(
                        kind: up ? "network.restored" : "network.offline",
                        detail: up ? "Suryadev iPad network restored" : "Suryadev iPad lost network connectivity",
                        severity: up ? "notice" : "warning"
                    )
                }
                if up { self.flushAlerts() }
                self.updateWorkLamp()
            }
        }
        pathMonitor.start(queue: networkQueue)
    }

    private func startTimers() {
        healthTimer = Timer.scheduledTimer(withTimeInterval: 15, repeats: true) { [weak self] _ in self?.healthTick() }
        sampleTimer = Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { [weak self] _ in self?.sampleYouTube() }
        learningTimer = Timer.scheduledTimer(withTimeInterval: 90, repeats: true) { [weak self] _ in self?.flushLearning() }
        healthTick()
    }

    @objc private func appActive() {
        forceScreenAwake()
        queueAlert(kind: "learning.resumed", detail: "Suryadev returned to foreground; always-on podcast learning resumed", severity: "notice")
    }

    @objc private func appInactive() {
        workLamp.set(false); learningLamp.set(false)
        queueAlert(kind: "learning.paused", detail: "Suryadev left foreground; iPadOS paused foreground podcast learning", severity: "warning")
    }

    @objc private func batteryChanged() { evaluateBattery() }
    @objc private func thermalChanged() {
        let x = ProcessInfo.processInfo.thermalState
        guard x != lastThermal else { return }
        lastThermal = x
        if x == .serious || x == .critical {
            queueAlert(kind: "thermal." + thermalName(x),
                       detail: "Suryadev iPad thermal state is " + thermalName(x),
                       severity: x == .critical ? "critical" : "warning")
        } else if x == .nominal {
            queueAlert(kind: "thermal.recovered", detail: "Suryadev iPad thermal state returned to nominal", severity: "notice")
        }
    }
    @objc private func powerChanged() {
        if ProcessInfo.processInfo.isLowPowerModeEnabled {
            queueAlert(kind: "power.low_mode", detail: "Low Power Mode is enabled; podcast learning performance may be reduced", severity: "warning")
        }
    }
    @objc private func memoryWarning() {
        queueAlert(kind: "memory.warning", detail: "iPadOS issued a memory warning to Suryadev", severity: "warning")
    }

    private func evaluateBattery() {
        let level = UIDevice.current.batteryLevel
        guard level >= 0 else { batteryLabel.text = "BAT --%"; return }
        let pct = Int((level * 100).rounded())
        batteryLabel.text = "BAT \(pct)%"
        if pct <= 50 && !battery50Sent {
            battery50Sent = true
            queueAlert(kind: "battery.50", detail: "Suryadev iPad battery reached \(pct)%", severity: "warning")
        } else if pct > 55 { battery50Sent = false }
        if pct <= 20 && !battery20Sent {
            battery20Sent = true
            queueAlert(kind: "battery.critical", detail: "Suryadev iPad battery is critical at \(pct)%", severity: "critical")
        } else if pct > 25 { battery20Sent = false }
    }

    private func healthTick() {
        forceScreenAwake()
        evaluateBattery()
        if let accepted = lastLearningAcceptedAt, Date().timeIntervalSince(accepted) > 210 {
            learningLamp.set(false)
        }
        let free = freeDiskBytes()
        if free > 0 && free < 1_000_000_000 {
            queueAlert(kind: "storage.low", detail: "Suryadev iPad has less than 1 GB free storage", severity: "warning")
        }
        guard client.configured else { linkLamp.set(false); return }
        let body = basePayload().merging([
            "youtube_url": latestURL,
            "youtube_title": latestTitle,
            "youtube_seconds": latestVideoTime,
            "youtube_playing": !latestPaused,
            "screen_awake": UIApplication.shared.isIdleTimerDisabled,
            "app_state": UIApplication.shared.applicationState == .active ? "foreground" : "background",
            "free_storage_bytes": free,
        ]) { _, new in new }
        client.heartbeat(body) { [weak self] code, obj in
            DispatchQueue.main.async {
                guard let self else { return }
                if (200..<300).contains(code) {
                    self.heartbeatFailures = 0
                    self.linkLamp.set(true)
                    self.workLamp.set(obj?["suryadev_working_green"] as? Bool ?? false)
                    self.learningLamp.set(obj?["rishi_learning_green"] as? Bool ?? (self.lastLearningAcceptedAt != nil))
                    self.flushAlerts()
                } else {
                    self.linkLamp.set(false)
                    self.heartbeatFailures += 1
                    if self.heartbeatFailures == 3 {
                        self.queueLocalOnlyAlert(kind: "core.unreachable", detail: "KRISHNA PC heartbeat failed three times", severity: "warning")
                    }
                }
            }
        }
    }

    private func basePayload() -> [String: Any] {
        let level = UIDevice.current.batteryLevel
        return [
            "device_id": client.deviceID,
            "node_name": "SURYADEV SHRAVANA — Podcast Gurukul",
            "device_role": "suryadev-ipad",
            "platform": "iPadOS",
            "hardware": machineIdentifier(),
            "battery_percent": level < 0 ? -1 : Int((level * 100).rounded()),
            "battery_state": batteryStateName(UIDevice.current.batteryState),
            "thermal_state": thermalName(ProcessInfo.processInfo.thermalState),
            "low_power_mode": ProcessInfo.processInfo.isLowPowerModeEnabled,
            "network_online": networkUp,
            "timestamp": Date().timeIntervalSince1970,
        ]
    }

    private func alertPacket(kind: String, detail: String, severity: String) -> [String: Any] {
        basePayload().merging(["kind": kind, "detail": detail, "severity": severity]) { _, new in new }
    }

    private func queueLocalOnlyAlert(kind: String, detail: String, severity: String) {
        pendingAlerts.append(alertPacket(kind: kind, detail: detail, severity: severity))
        if pendingAlerts.count > 50 { pendingAlerts.removeFirst(pendingAlerts.count - 50) }
        persistAlerts()
    }

    private func queueAlert(kind: String, detail: String, severity: String) {
        queueLocalOnlyAlert(kind: kind, detail: detail, severity: severity)
        flushAlerts()
    }

    private func flushAlerts() {
        guard networkUp, client.configured, !pendingAlerts.isEmpty else { return }
        let row = pendingAlerts[0]
        client.alert(row) { [weak self] code, _ in
            DispatchQueue.main.async {
                guard let self else { return }
                if (200..<300).contains(code) {
                    if !self.pendingAlerts.isEmpty { self.pendingAlerts.removeFirst() }
                    self.persistAlerts()
                    if !self.pendingAlerts.isEmpty { self.flushAlerts() }
                }
            }
        }
    }

    private func persistAlerts() {
        if let data = try? JSONSerialization.data(withJSONObject: pendingAlerts) {
            UserDefaults.standard.set(data, forKey: "suryadev.pending.alerts")
        }
    }
    private func restoreAlerts() {
        guard let data = UserDefaults.standard.data(forKey: "suryadev.pending.alerts"),
              let rows = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]] else { return }
        pendingAlerts = Array(rows.suffix(50))
    }

    private func checkPairingAndQueue() {
        guard client.configured else { linkLamp.set(false); return }
        client.bootstrap { [weak self] code, _ in
            DispatchQueue.main.async {
                guard let self else { return }
                if (200..<300).contains(code) {
                    self.linkLamp.set(true); self.fetchQueue()
                } else if code == 401 {
                    self.linkLamp.set(false)
                    self.client.requestPairing { _, _ in }
                } else {
                    self.linkLamp.set(false)
                }
            }
        }
    }

    private func fetchQueue() {
        client.queue { [weak self] code, obj in
            DispatchQueue.main.async {
                guard let self, (200..<300).contains(code), let rows = obj?["items"] as? [[String: Any]] else { return }
                self.queueItems = rows.compactMap { row in
                    guard let show = row["show"] as? String, !show.isEmpty else { return nil }
                    return PodcastQueueItem(
                        rank: row["rank"] as? Int ?? 0,
                        show: show,
                        youtubeURL: row["youtube_url"] as? String ?? "",
                        youtubeSearch: row["youtube_search"] as? String ?? ""
                    )
                }
                self.queueLabel.text = "QUEUE \(self.queueItems.count)/30"
            }
        }
    }

    @objc private func showQueue() {
        if queueItems.isEmpty { fetchQueue(); return }
        let q = PodcastQueueViewController(items: queueItems) { [weak self] item in
            self?.openPodcast(item)
        }
        present(q, animated: true)
    }

    private func openPodcast(_ item: PodcastQueueItem) {
        selectedShow = item.show
        learningBuffer.removeAll(keepingCapacity: true)
        learningStart = 0
        lastLearningAcceptedAt = nil
        learningLamp.set(false)
        selectedLabel.text = "PODCAST · #\(item.rank) · \(item.show)"
        let raw = item.youtubeURL.isEmpty ? item.youtubeSearch : item.youtubeURL
        if let u = URL(string: raw), isYouTubeURL(u.absoluteString) {
            web.load(URLRequest(url: u))
        }
    }

    @objc private func showLearning() {
        guard client.configured else {
            showMessage("WHAT I LEARNED", "KRISHNA PC is not configured yet.")
            return
        }
        client.status { [weak self] code, obj in
            DispatchQueue.main.async {
                guard let self else { return }
                guard (200..<300).contains(code), let obj else {
                    self.showMessage("WHAT I LEARNED", "Unable to read this node's learning status from KRISHNA PC.")
                    return
                }
                let title = obj["last_learning_title"] as? String ?? "No accepted podcast learning yet"
                let finding = obj["last_learning_finding_id"] as? String ?? "—"
                let green = obj["rishi_learning_green"] as? Bool ?? false
                let age = obj["learning_age_seconds"] as? Double
                let ageText = age == nil ? "—" : String(format: "%.0f sec", age!)
                self.showMessage(
                    "WHAT I LEARNED",
                    "Node: \(self.client.deviceID)\nRishi: Shravana\nLearning: \(green ? "GREEN" : "RED")\nLatest: \(title)\nFinding: \(finding)\nAge: \(ageText)"
                )
            }
        }
    }

    @objc private func showResearch() {
        present(ResearchViewController(client: client), animated: true)
    }

    @objc private func reload() { web.reload() }

    @objc private func configureCore() {
        let a = UIAlertController(
            title: "Pair with KRISHNA PC",
            message: "Enter only the trusted private KRISHNA address. After Save & Pair, approve this Node ID on the KRISHNA PC.",
            preferredStyle: .alert
        )
        a.addTextField { f in
            f.placeholder = "http://192.168.x.x:8766"
            f.text = self.client.baseURL
            f.keyboardType = .URL
            f.autocapitalizationType = .none
        }
        a.addAction(UIAlertAction(title: "Save & Pair", style: .default) { [weak self, weak a] _ in
            guard let self else { return }
            self.client.baseURL = a?.textFields?.first?.text ?? ""
            guard self.client.configured else { self.linkLamp.set(false); return }
            self.client.requestPairing { [weak self] code, _ in
                DispatchQueue.main.async {
                    self?.linkLamp.set(false)
                    if (200..<300).contains(code) {
                        self?.showMessage("Pairing requested", "Approve Node ID:\n\(self?.client.deviceID ?? "")\non KRISHNA PC. The app will keep checking automatically.")
                    } else {
                        self?.showMessage("Pairing failed", "Check KRISHNA PC address and Wi-Fi/private network.")
                    }
                }
            }
        })
        a.addAction(UIAlertAction(title: "Cancel", style: .cancel))
        present(a, animated: true)
    }

    private func showMessage(_ title: String, _ text: String) {
        let a = UIAlertController(title: title, message: text, preferredStyle: .alert)
        a.addAction(UIAlertAction(title: "OK", style: .default))
        present(a, animated: true)
    }

    private func sampleYouTube() {
        guard !selectedShow.isEmpty else { updateWorkLamp(); return }
        let js = """
        (() => {
          const v=document.querySelector('video');
          const title=(document.title||'').replace(/\\s*-\\s*YouTube\\s*$/i,'').trim();
          const caps=[...document.querySelectorAll('.ytp-caption-segment')].map(x=>(x.innerText||'').trim()).filter(Boolean).join(' ');
          return JSON.stringify({url:location.href,title,seconds:v?Number(v.currentTime||0):0,paused:v?!!v.paused:true,caption:caps});
        })()
        """
        web.evaluateJavaScript(js) { [weak self] raw, _ in
            guard let self, let s = raw as? String, let data = s.data(using: .utf8),
                  let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                self?.updateWorkLamp(); return
            }
            let url = obj["url"] as? String ?? ""
            guard self.isYouTubeURL(url) else { self.updateWorkLamp(); return }
            self.latestURL = String(url.prefix(1500))
            self.latestTitle = String((obj["title"] as? String ?? "").prefix(500))
            self.latestVideoTime = obj["seconds"] as? Double ?? 0
            self.latestPaused = obj["paused"] as? Bool ?? true
            let caption = (obj["caption"] as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            if self.learningStart == 0 { self.learningStart = self.latestVideoTime }
            if !caption.isEmpty && self.learningBuffer.last != caption {
                self.learningBuffer.append(String(caption.prefix(1200)))
                if self.learningBuffer.count > 80 { self.learningBuffer.removeFirst(self.learningBuffer.count - 80) }
            }
            self.updateWorkLamp()
        }
    }

    private func flushLearning() {
        guard !selectedShow.isEmpty, !latestURL.isEmpty else { learningLamp.set(false); return }
        let text = learningBuffer.joined(separator: " ")
            .replacingOccurrences(of: "\\s+", with: " ", options: .regularExpression)
        let body = basePayload().merging([
            "queue_show": selectedShow,
            "source_type": "youtube_foreground_podcast_observation",
            "source_url": latestURL,
            "title": latestTitle,
            "start_seconds": learningStart,
            "end_seconds": latestVideoTime,
            "visible_caption_text": String(text.prefix(6000)),
            "caption_available": !text.isEmpty,
            "raw_media_included": false,
            "observation_seconds": max(0, Date().timeIntervalSince(lastLearningFlush)),
        ]) { _, new in new }
        client.learning(body) { [weak self] code, obj in
            DispatchQueue.main.async {
                guard let self else { return }
                let green = (200..<300).contains(code) && (obj?["learning_green"] as? Bool ?? false)
                self.learningLamp.set(green)
                if green {
                    self.lastLearningAcceptedAt = Date()
                    self.learningBuffer.removeAll(keepingCapacity: true)
                    self.learningStart = self.latestVideoTime
                    self.lastLearningFlush = Date()
                }
            }
        }
    }

    private func updateWorkLamp() {
        let foreground = UIApplication.shared.applicationState == .active
        workLamp.set(networkUp && foreground && UIApplication.shared.isIdleTimerDisabled && !selectedShow.isEmpty && isYouTubeURL(latestURL) && !latestPaused)
    }

    private func allowedYouTubeHost(_ host: String) -> Bool {
        let h = host.lowercased()
        return h == "youtu.be" || h == "youtube.com" || h.hasSuffix(".youtube.com") ||
               h == "google.com" || h.hasSuffix(".google.com")
    }
    private func isYouTubeURL(_ raw: String) -> Bool {
        guard let u = URL(string: raw), let h = u.host else { return false }
        let x = h.lowercased()
        return x == "youtu.be" || x == "youtube.com" || x.hasSuffix(".youtube.com")
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard action.targetFrame?.isMainFrame ?? true else { decisionHandler(.allow); return }
        guard let url = action.request.url, let host = url.host else { decisionHandler(.cancel); return }
        decisionHandler(allowedYouTubeHost(host) ? .allow : .cancel)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        sampleYouTube()
    }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        workLamp.set(false)
        queueAlert(kind: "youtube.navigation_error", detail: "Podcast browser navigation failed: \(error.localizedDescription)", severity: "warning")
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        workLamp.set(false)
        queueAlert(kind: "youtube.load_error", detail: "Podcast page load failed: \(error.localizedDescription)", severity: "warning")
    }
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        workLamp.set(false); learningLamp.set(false)
        queueAlert(kind: "youtube.web_process_crash", detail: "YouTube WebKit process terminated; Suryadev reloaded it", severity: "warning")
        webView.reload()
    }

    private func freeDiskBytes() -> Int {
        let v = try? URL(fileURLWithPath: NSHomeDirectory()).resourceValues(forKeys: [.volumeAvailableCapacityForImportantUsageKey])
        return Int(v?.volumeAvailableCapacityForImportantUsage ?? 0)
    }
    private func machineIdentifier() -> String {
        var info = utsname(); uname(&info)
        let mirror = Mirror(reflecting: info.machine)
        return mirror.children.reduce("") { out, child in
            guard let v = child.value as? Int8, v != 0 else { return out }
            return out + String(UnicodeScalar(UInt8(v)))
        }
    }
    private func batteryStateName(_ x: UIDevice.BatteryState) -> String {
        switch x {
        case .charging: return "charging"
        case .full: return "full"
        case .unplugged: return "unplugged"
        default: return "unknown"
        }
    }
    private func thermalName(_ x: ProcessInfo.ThermalState) -> String {
        switch x {
        case .nominal: return "nominal"
        case .fair: return "fair"
        case .serious: return "serious"
        case .critical: return "critical"
        @unknown default: return "unknown"
        }
    }
}
