import UIKit
import WebKit
import Network
import Security
import CryptoKit

@main
final class SuryadevHorseAppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let w = UIWindow(frame: UIScreen.main.bounds)
        w.rootViewController = SuryadevHorseViewController()
        w.makeKeyAndVisible()
        window = w
        return true
    }
}

final class SecureStore {
    private static let service = "com.krishna.suryadev.horse"
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
        var add = q
        add[kSecValueData as String] = Data(value.utf8)
        add[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        SecItemAdd(add as CFDictionary, nil)
    }
}

final class CoreClient {
    let deviceID: String
    let credential: String
    private let defaults = UserDefaults.standard

    var baseURL: String {
        get { defaults.string(forKey: "suryadev.core.url") ?? "" }
        set {
            let cleaned = newValue.trimmingCharacters(in: .whitespacesAndNewlines)
                .replacingOccurrences(of: "/+$", with: "", options: .regularExpression)
            defaults.set(cleaned, forKey: "suryadev.core.url")
        }
    }

    init() {
        if let v = SecureStore.read("device-id") {
            deviceID = v
        } else {
            let v = "suryadev-ios-" + UUID().uuidString.lowercased()
            SecureStore.write(v, key: "device-id")
            deviceID = v
        }
        if let v = SecureStore.read("device-credential") {
            credential = v
        } else {
            let v = UUID().uuidString + "-" + UUID().uuidString + "-" + UUID().uuidString
            SecureStore.write(v, key: "device-credential")
            credential = v
        }
    }

    var configured: Bool {
        guard let u = URL(string: baseURL), let host = u.host?.lowercased(),
              u.scheme == "http" || u.scheme == "https" else { return false }
        if host == "localhost" || host.hasSuffix(".local") || host.hasSuffix(".ts.net") { return true }
        let parts = host.split(separator: ".").compactMap { Int($0) }
        if parts.count == 4 && parts.allSatisfy({ (0...255).contains($0) }) {
            if parts[0] == 10 || (parts[0] == 192 && parts[1] == 168) { return true }
            if parts[0] == 172 && (16...31).contains(parts[1]) { return true }
            if parts[0] == 100 && (64...127).contains(parts[1]) { return true }
        }
        return false
    }

    private func request(_ path: String, method: String = "GET", body: [String: Any]? = nil,
                         authenticated: Bool = true,
                         timeout: TimeInterval = 20,
                         completion: @escaping (Int, [String: Any]?) -> Void) {
        guard configured, let url = URL(string: baseURL + path) else {
            completion(0, ["error": "trusted private KRISHNA Core URL is not configured"])
            return
        }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.timeoutInterval = timeout
        req.cachePolicy = .reloadIgnoringLocalCacheData
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if authenticated {
            req.setValue(deviceID, forHTTPHeaderField: "X-Krishna-Device")
            req.setValue("Device " + credential, forHTTPHeaderField: "Authorization")
        } else {
            req.setValue(deviceID, forHTTPHeaderField: "X-Krishna-Device")
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
        let digest = SHA256.hash(data: Data(credential.utf8))
            .map { String(format: "%02x", $0) }.joined()
        request("/api/mobile/pair/request", method: "POST", body: [
            "device_id": deviceID,
            "name": "SURYADEV iPad Learning Node",
            "credential_sha256": digest,
        ], authenticated: false, completion: completion)
    }

    func bootstrap(_ completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/mobile/bootstrap", completion: completion)
    }
    func sendProfile(_ profile: [String: Any], completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/suryadev/horse/profile", method: "POST",
                body: ["profile": profile, "label": "SURYDEV iPad learning node"],
                completion: completion)
    }
    func assignment(_ completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/suryadev/horse/assignment", completion: completion)
    }
    func curriculum(_ completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/suryadev/horse/curriculum", completion: completion)
    }
    func nextCurriculum(_ completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/suryadev/horse/curriculum/next", method: "POST",
                body: ["max_videos": 10, "candidate_limit": 40, "enrich_metadata": true],
                timeout: 120, completion: completion)
    }
    func heartbeat(_ status: [String: Any], completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/suryadev/horse/heartbeat", method: "POST",
                body: ["status": status], completion: completion)
    }
    func learningBatch(_ batch: [String: Any], completion: @escaping (Int, [String: Any]?) -> Void) {
        request("/api/suryadev/horse/learning", method: "POST",
                body: ["batch": batch], timeout: 45, completion: completion)
    }
}

final class Lamp: UIView {
    private let dot = UIView()
    private let text = UILabel()
    init(_ label: String) {
        super.init(frame: .zero)
        translatesAutoresizingMaskIntoConstraints = false
        dot.translatesAutoresizingMaskIntoConstraints = false
        dot.layer.cornerRadius = 5
        text.translatesAutoresizingMaskIntoConstraints = false
        text.text = label
        text.font = .monospacedSystemFont(ofSize: 10, weight: .semibold)
        text.textColor = .white
        addSubview(dot); addSubview(text)
        NSLayoutConstraint.activate([
            dot.leadingAnchor.constraint(equalTo: leadingAnchor),
            dot.centerYAnchor.constraint(equalTo: centerYAnchor),
            dot.widthAnchor.constraint(equalToConstant: 10),
            dot.heightAnchor.constraint(equalToConstant: 10),
            text.leadingAnchor.constraint(equalTo: dot.trailingAnchor, constant: 5),
            text.trailingAnchor.constraint(equalTo: trailingAnchor),
            text.topAnchor.constraint(equalTo: topAnchor),
            text.bottomAnchor.constraint(equalTo: bottomAnchor),
        ])
        set(false)
    }
    required init?(coder: NSCoder) { fatalError() }
    func set(_ green: Bool) {
        dot.backgroundColor = green ? .systemGreen : .systemRed
        dot.layer.shadowColor = dot.backgroundColor?.cgColor
        dot.layer.shadowOpacity = 0.75
        dot.layer.shadowRadius = 4
        dot.layer.shadowOffset = .zero
    }
}

struct LessonItem {
    let order: Int
    let url: String
    let title: String
    let channel: String
    let description: String
    let tags: [String]
    let duration: Double

    init?(_ row: [String: Any]) {
        guard let u = row["url"] as? String, !u.isEmpty else { return nil }
        url = u
        order = row["order"] as? Int ?? 0
        title = row["title"] as? String ?? "YouTube lesson"
        channel = row["channel"] as? String ?? row["source"] as? String ?? ""
        description = row["description"] as? String ?? row["summary"] as? String ?? ""
        tags = row["tags"] as? [String] ?? []
        if let d = row["duration_seconds"] as? Double { duration = d }
        else if let d = row["duration_seconds"] as? Int { duration = Double(d) }
        else { duration = 0 }
    }
}

final class SuryadevHorseViewController: UIViewController, WKNavigationDelegate, WKUIDelegate {
    private let client = CoreClient()
    private let defaults = UserDefaults.standard
    private let monitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "suryadev.horse.network")

    private var web: WKWebView!
    private let serverLamp = Lamp("SERVER LINK")
    private let workLamp = Lamp("SURYADEV WORKING")
    private let learnLamp = Lamp("LEARNING")
    private let brand = UILabel()
    private let nodeLabel = UILabel()
    private let assignmentLabel = UILabel()
    private let subjectLabel = UILabel()
    private let progressLabel = UILabel()
    private let batteryLabel = UILabel()

    private var networkUp = false
    private var healthTimer: Timer?
    private var sampleTimer: Timer?
    private var horseID = ""
    private var horseName = ""
    private var workload = ""
    private var planID = ""
    private var subject = ""
    private var playlist: [LessonItem] = []
    private var index = 0
    private var latestURL = ""
    private var latestTitle = ""
    private var latestTime: Double = 0
    private var latestDuration: Double = 0
    private var latestPaused = true
    private var priorVideoTime: Double = 0
    private var shiftWatchSeconds: Double = 0
    private var shiftStartedAt: Double = 0
    private var transcriptChunks: [String] = []
    private var completedSources: [[String: Any]] = []
    private var lastPersist = Date()
    private var uploading = false

    override func viewDidLoad() {
        super.viewDidLoad()
        UIDevice.current.isBatteryMonitoringEnabled = true
        view.backgroundColor = UIColor(red: 0.008, green: 0.025, blue: 0.045, alpha: 1)
        setupWeb()
        setupUI()
        restoreLocalBatch()
        registerSystemObservers()
        startNetworkMonitor()
        startTimers()
        keepAwake()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { [weak self] in self?.connect() }
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        keepAwake()
    }

    deinit {
        healthTimer?.invalidate(); sampleTimer?.invalidate()
        monitor.cancel()
        NotificationCenter.default.removeObserver(self)
        UIApplication.shared.isIdleTimerDisabled = false
    }

    private func setupWeb() {
        let cfg = WKWebViewConfiguration()
        cfg.allowsInlineMediaPlayback = true
        cfg.allowsPictureInPictureMediaPlayback = false
        cfg.mediaTypesRequiringUserActionForPlayback = []
        cfg.websiteDataStore = .default()
        web = WKWebView(frame: .zero, configuration: cfg)
        web.translatesAutoresizingMaskIntoConstraints = false
        web.navigationDelegate = self
        web.uiDelegate = self
        web.backgroundColor = .black
        web.allowsBackForwardNavigationGestures = false
    }

    private func setupUI() {
        let header = UIView()
        header.translatesAutoresizingMaskIntoConstraints = false
        header.backgroundColor = UIColor(red: 0.015, green: 0.075, blue: 0.11, alpha: 0.98)

        brand.translatesAutoresizingMaskIntoConstraints = false
        brand.text = "☀︎ SURYADEV · UNASSIGNED HORSE"
        brand.font = .systemFont(ofSize: 14, weight: .bold)
        brand.textColor = UIColor(red: 1.0, green: 0.82, blue: 0.35, alpha: 1)

        nodeLabel.translatesAutoresizingMaskIntoConstraints = false
        nodeLabel.text = "NODE · " + client.deviceID
        nodeLabel.font = .monospacedSystemFont(ofSize: 8.5, weight: .medium)
        nodeLabel.textColor = .systemTeal
        nodeLabel.adjustsFontSizeToFitWidth = true
        nodeLabel.minimumScaleFactor = 0.6

        assignmentLabel.translatesAutoresizingMaskIntoConstraints = false
        assignmentLabel.text = "WORKLOAD · WAITING"
        assignmentLabel.font = .monospacedSystemFont(ofSize: 9, weight: .semibold)
        assignmentLabel.textColor = UIColor.white.withAlphaComponent(0.8)

        subjectLabel.translatesAutoresizingMaskIntoConstraints = false
        subjectLabel.text = "SUBJECT · waiting for BRAHMA curriculum"
        subjectLabel.font = .systemFont(ofSize: 11, weight: .semibold)
        subjectLabel.textColor = .white
        subjectLabel.numberOfLines = 1
        subjectLabel.adjustsFontSizeToFitWidth = true
        subjectLabel.minimumScaleFactor = 0.55

        progressLabel.translatesAutoresizingMaskIntoConstraints = false
        progressLabel.font = .monospacedSystemFont(ofSize: 9, weight: .regular)
        progressLabel.textColor = UIColor.white.withAlphaComponent(0.78)
        progressLabel.text = "0:00 / 6:00"

        batteryLabel.translatesAutoresizingMaskIntoConstraints = false
        batteryLabel.font = .monospacedSystemFont(ofSize: 9, weight: .bold)
        batteryLabel.textColor = .white
        batteryLabel.text = "BAT --%"

        let lamps = UIStackView(arrangedSubviews: [serverLamp, workLamp, learnLamp])
        lamps.translatesAutoresizingMaskIntoConstraints = false
        lamps.axis = .horizontal
        lamps.spacing = 14
        lamps.alignment = .center

        let pair = button("PAIR", #selector(configureCore))
        let curriculum = button("CURRICULUM", #selector(reloadCurriculum))
        let reload = button("RELOAD", #selector(reloadPage))
        let buttons = UIStackView(arrangedSubviews: [pair, curriculum, reload])
        buttons.translatesAutoresizingMaskIntoConstraints = false
        buttons.axis = .horizontal
        buttons.spacing = 8

        [brand,nodeLabel,assignmentLabel,subjectLabel,progressLabel,batteryLabel,lamps,buttons].forEach { header.addSubview($0) }
        view.addSubview(header); view.addSubview(web)

        NSLayoutConstraint.activate([
            header.topAnchor.constraint(equalTo: view.topAnchor),
            header.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            header.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            header.heightAnchor.constraint(equalToConstant: 118),

            brand.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 5),
            brand.leadingAnchor.constraint(equalTo: header.leadingAnchor, constant: 12),
            nodeLabel.topAnchor.constraint(equalTo: brand.bottomAnchor, constant: 2),
            nodeLabel.leadingAnchor.constraint(equalTo: brand.leadingAnchor),
            nodeLabel.widthAnchor.constraint(equalTo: header.widthAnchor, multiplier: 0.48),

            assignmentLabel.topAnchor.constraint(equalTo: nodeLabel.bottomAnchor, constant: 2),
            assignmentLabel.leadingAnchor.constraint(equalTo: brand.leadingAnchor),
            assignmentLabel.widthAnchor.constraint(equalTo: header.widthAnchor, multiplier: 0.48),

            subjectLabel.topAnchor.constraint(equalTo: assignmentLabel.bottomAnchor, constant: 4),
            subjectLabel.leadingAnchor.constraint(equalTo: brand.leadingAnchor),
            subjectLabel.widthAnchor.constraint(equalTo: header.widthAnchor, multiplier: 0.64),

            lamps.topAnchor.constraint(equalTo: brand.topAnchor),
            lamps.trailingAnchor.constraint(equalTo: header.trailingAnchor, constant: -12),

            batteryLabel.topAnchor.constraint(equalTo: lamps.bottomAnchor, constant: 6),
            batteryLabel.trailingAnchor.constraint(equalTo: header.trailingAnchor, constant: -12),

            progressLabel.topAnchor.constraint(equalTo: batteryLabel.bottomAnchor, constant: 4),
            progressLabel.trailingAnchor.constraint(equalTo: header.trailingAnchor, constant: -12),

            buttons.bottomAnchor.constraint(equalTo: header.bottomAnchor, constant: -7),
            buttons.trailingAnchor.constraint(equalTo: header.trailingAnchor, constant: -12),

            web.topAnchor.constraint(equalTo: header.bottomAnchor),
            web.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            web.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            web.bottomAnchor.constraint(equalTo: view.bottomAnchor),
        ])
    }

    private func button(_ title: String, _ action: Selector) -> UIButton {
        let b = UIButton(type: .system)
        b.setTitle(title, for: .normal)
        b.setTitleColor(.white, for: .normal)
        b.titleLabel?.font = .systemFont(ofSize: 9.5, weight: .bold)
        b.backgroundColor = UIColor.white.withAlphaComponent(0.10)
        b.layer.cornerRadius = 6
        b.contentEdgeInsets = UIEdgeInsets(top: 4, left: 9, bottom: 4, right: 9)
        b.addTarget(self, action: action, for: .touchUpInside)
        return b
    }

    private func keepAwake() { UIApplication.shared.isIdleTimerDisabled = true }

    private func registerSystemObservers() {
        let n = NotificationCenter.default
        n.addObserver(self, selector: #selector(appActive), name: UIApplication.didBecomeActiveNotification, object: nil)
        n.addObserver(self, selector: #selector(appInactive), name: UIApplication.willResignActiveNotification, object: nil)
        n.addObserver(self, selector: #selector(memoryWarning), name: UIApplication.didReceiveMemoryWarningNotification, object: nil)
        n.addObserver(self, selector: #selector(thermalChanged), name: ProcessInfo.thermalStateDidChangeNotification, object: nil)
        n.addObserver(self, selector: #selector(batteryChanged), name: UIDevice.batteryLevelDidChangeNotification, object: nil)
    }
    @objc private func appActive() { keepAwake(); updateLights() }
    @objc private func appInactive() { workLamp.set(false); learnLamp.set(false) }
    @objc private func memoryWarning() { persistLocalBatch() }
    @objc private func thermalChanged() { healthTick() }
    @objc private func batteryChanged() { updateBattery() }

    private func startNetworkMonitor() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.networkUp = path.status == .satisfied
                self?.updateLights()
            }
        }
        monitor.start(queue: monitorQueue)
    }

    private func startTimers() {
        healthTimer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in self?.healthTick() }
        sampleTimer = Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { [weak self] _ in self?.sampleVideo() }
        healthTick()
    }

    private func connect() {
        guard client.configured else {
            serverLamp.set(false)
            configureCore()
            return
        }
        client.bootstrap { [weak self] code, _ in
            DispatchQueue.main.async {
                guard let self else { return }
                if code == 200 {
                    self.serverLamp.set(true)
                    self.registerProfile()
                } else if code == 401 {
                    self.serverLamp.set(false)
                    self.client.requestPairing { _, _ in }
                } else {
                    self.serverLamp.set(false)
                }
            }
        }
    }

    private func registerProfile() {
        client.sendProfile(deviceProfile()) { [weak self] code, obj in
            DispatchQueue.main.async {
                guard let self else { return }
                guard code == 200, let obj,
                      let binding = obj["binding"] as? [String: Any] else {
                    self.serverLamp.set(false); return
                }
                self.serverLamp.set(true)
                self.horseID = binding["horse_id"] as? String ?? ""
                self.workload = binding["workload"] as? String ?? ""
                self.horseName = self.horseID.isEmpty ? "HORSE" : self.horseID.uppercased()
                self.brand.text = "☀︎ SURYADEV · " + self.horseName
                self.assignmentLabel.text = "WORKLOAD · " + self.workload.uppercased()
                self.fetchCurriculum(createIfMissing: true)
            }
        }
    }

    @objc private func reloadCurriculum() { fetchCurriculum(createIfMissing: true) }
    @objc private func reloadPage() { web.reload() }

    private func fetchCurriculum(createIfMissing: Bool) {
        guard !horseID.isEmpty, workload == "media_learning" || workload == "hybrid" else { return }
        client.curriculum { [weak self] code, obj in
            DispatchQueue.main.async {
                guard let self else { return }
                if code == 200, let obj { self.loadCurriculum(obj); return }
                if code == 404 && createIfMissing {
                    self.subjectLabel.text = "BRAHMA · preparing next 6-hour curriculum…"
                    self.client.nextCurriculum { [weak self] nextCode, nextObj in
                        DispatchQueue.main.async {
                            guard let self else { return }
                            if nextCode == 200, let nextObj { self.loadCurriculum(nextObj) }
                            else { self.learnLamp.set(false) }
                        }
                    }
                }
            }
        }
    }

    private func loadCurriculum(_ plan: [String: Any]) {
        guard let rows = plan["playlist"] as? [[String: Any]] else { return }
        let items = rows.compactMap(LessonItem.init)
        guard !items.isEmpty else { learnLamp.set(false); return }
        let incomingPlan = plan["plan_id"] as? String ?? ""
        if incomingPlan != planID {
            if !planID.isEmpty && !completedSources.isEmpty {
                subjectLabel.text = "PENDING UPLOAD · local batch retained before new curriculum"
                learnLamp.set(false)
                return
            }
            // Safe reset only when there is no unsent evidence. Normal cleanup after
            // a completed shift happens exclusively after a positive server receipt.
            completedSources.removeAll()
            transcriptChunks.removeAll()
            shiftWatchSeconds = 0
            shiftStartedAt = 0
            planID = incomingPlan
            subject = plan["subject"] as? String ?? "BRAHMA learning"
            playlist = items
            index = 0
            shiftStartedAt = Date().timeIntervalSince1970
            shiftWatchSeconds = 0
            defaults.set(planID, forKey: "horse.plan.id")
            defaults.set(subject, forKey: "horse.plan.subject")
            defaults.set(index, forKey: "horse.plan.index")
            defaults.set(shiftStartedAt, forKey: "horse.shift.started")
            defaults.set(shiftWatchSeconds, forKey: "horse.shift.watch")
        } else {
            playlist = items
            index = min(defaults.integer(forKey: "horse.plan.index"), max(0, items.count - 1))
        }
        subjectLabel.text = "SUBJECT · " + subject
        openCurrentLesson()
        persistLocalBatch()
    }

    private func openCurrentLesson() {
        guard index >= 0, index < playlist.count else {
            finishBatch(reason: "playlist_complete")
            return
        }
        let item = playlist[index]
        guard let url = URL(string: item.url), isYouTube(item.url) else {
            index += 1; defaults.set(index, forKey: "horse.plan.index"); openCurrentLesson(); return
        }
        latestURL = item.url
        latestTitle = item.title
        latestTime = 0
        latestDuration = item.duration
        priorVideoTime = 0
        transcriptChunks.removeAll(keepingCapacity: true)
        web.load(URLRequest(url: url))
        updateProgress()
    }

    private func sampleVideo() {
        guard !planID.isEmpty, index < playlist.count else { updateLights(); return }
        let js = """
        (() => {
          const v=document.querySelector('video');
          const caps=[...document.querySelectorAll('.ytp-caption-segment')]
            .map(x=>(x.innerText||'').trim()).filter(Boolean).join(' ');
          return JSON.stringify({
            url:location.href,
            title:(document.title||'').replace(/\s*-\s*YouTube\s*$/i,'').trim(),
            current:v?Number(v.currentTime||0):0,
            duration:v&&Number.isFinite(v.duration)?Number(v.duration):0,
            paused:v?!!v.paused:true,
            ended:v?!!v.ended:false,
            caption:caps
          });
        })()
        """
        web.evaluateJavaScript(js) { [weak self] raw, _ in
            guard let self, let raw = raw as? String, let data = raw.data(using: .utf8),
                  let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                self?.updateLights(); return
            }
            let url = obj["url"] as? String ?? ""
            guard self.isYouTube(url) else { self.updateLights(); return }
            let current = obj["current"] as? Double ?? 0
            let duration = obj["duration"] as? Double ?? self.latestDuration
            let paused = obj["paused"] as? Bool ?? true
            let ended = obj["ended"] as? Bool ?? false
            let caption = (obj["caption"] as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines)

            if !paused && current >= self.priorVideoTime {
                let delta = min(8.0, max(0.0, current - self.priorVideoTime))
                if self.priorVideoTime > 0 { self.shiftWatchSeconds += delta }
            }
            self.priorVideoTime = current
            self.latestTime = current
            self.latestDuration = duration > 0 ? duration : self.latestDuration
            self.latestPaused = paused
            self.latestURL = url
            if let t = obj["title"] as? String, !t.isEmpty { self.latestTitle = String(t.prefix(600)) }

            if !caption.isEmpty && self.transcriptChunks.last != caption {
                self.transcriptChunks.append(String(caption.prefix(1000)))
                if self.transcriptChunks.count > 120 {
                    self.transcriptChunks.removeFirst(self.transcriptChunks.count - 120)
                }
            }
            self.updateProgress()
            self.updateLights()

            if Date().timeIntervalSince(self.lastPersist) > 30 {
                self.persistLocalBatch(); self.lastPersist = Date()
            }

            if ended {
                self.finalizeCurrentSource(partial: false)
                self.index += 1
                self.defaults.set(self.index, forKey: "horse.plan.index")
                self.openCurrentLesson()
                return
            }

            if self.shiftWatchSeconds >= 21_600 {
                let remaining = self.latestDuration > 0 ? max(0, self.latestDuration - self.latestTime) : nil
                if let remaining, remaining > 0 && remaining <= 300 {
                    return
                }
                self.finalizeCurrentSource(partial: true)
                self.finishBatch(reason: "six_hour_boundary")
            }
        }
    }

    private func finalizeCurrentSource(partial: Bool) {
        guard index >= 0, index < playlist.count else { return }
        let item = playlist[index]
        let transcript = transcriptChunks.joined(separator: " ")
            .replacingOccurrences(of: "\s+", with: " ", options: .regularExpression)
        let row: [String: Any] = [
            "url": item.url,
            "title": item.title.isEmpty ? latestTitle : item.title,
            "description": item.description,
            "tags": item.tags,
            "publisher": item.channel,
            "source_kind": "youtube",
            "start_seconds": 0,
            "end_seconds": partial ? latestTime : max(latestTime, item.duration),
            "duration_seconds": item.duration > 0 ? item.duration : latestDuration,
            "transcript_excerpt": String(transcript.prefix(12_000)),
            "screen_notes": partial ? "Foreground lesson checkpointed at six-hour boundary." : "Foreground lesson reached end of video.",
        ]
        let key = item.url + "|" + String(Int(row["end_seconds"] as? Double ?? 0))
        let existing = completedSources.contains { (($0["url"] as? String) ?? "") + "|" + String(Int($0["end_seconds"] as? Double ?? 0)) == key }
        if !existing { completedSources.append(row) }
        if completedSources.count > 16 { completedSources.removeFirst(completedSources.count - 16) }
        transcriptChunks.removeAll(keepingCapacity: true)
        persistLocalBatch()
    }

    private func finishBatch(reason: String) {
        guard !uploading, !planID.isEmpty, !completedSources.isEmpty else { return }
        uploading = true
        learnLamp.set(false)
        let batch: [String: Any] = [
            "curriculum_plan_id": planID,
            "shift_name": subject,
            "started_at": shiftStartedAt,
            "ended_at": Date().timeIntervalSince1970,
            "watch_seconds": shiftWatchSeconds,
            "finish_reason": reason,
            "sources": completedSources,
        ]
        client.learningBatch(batch) { [weak self] code, obj in
            DispatchQueue.main.async {
                guard let self else { return }
                self.uploading = false
                let accepted = code == 200 && (obj?["cleanup_allowed"] as? Bool ?? false)
                self.learnLamp.set(accepted)
                if accepted {
                    self.clearTransientBatch()
                    self.planID = ""; self.subject = ""; self.playlist = []; self.index = 0
                    self.subjectLabel.text = "BRAHMA · preparing next subject…"
                    self.fetchCurriculum(createIfMissing: true)
                } else {
                    self.persistLocalBatch()
                }
            }
        }
    }

    private func healthTick() {
        keepAwake()
        updateBattery()
        guard client.configured, !horseID.isEmpty else { serverLamp.set(false); return }
        var status: [String: Any] = [
            "network_ok": networkUp,
            "screen_understanding_ok": !planID.isEmpty && UIApplication.shared.applicationState == .active,
            "learning_ok": !planID.isEmpty && !latestPaused,
            "media_playing": !latestPaused,
            "current_url": latestURL,
            "current_title": latestTitle,
            "current_shift": subject,
            "charging": UIDevice.current.batteryState == .charging || UIDevice.current.batteryState == .full,
            "thermal_state": thermalName(ProcessInfo.processInfo.thermalState),
            "free_storage_bytes": freeDiskBytes(),
            "pending_batches": completedSources.isEmpty ? 0 : 1,
        ]
        if let battery = batteryPercent() { status["battery_percent"] = battery }
        client.heartbeat(status) { [weak self] code, _ in
            DispatchQueue.main.async {
                self?.serverLamp.set(code == 200)
                self?.updateLights()
            }
        }
    }

    private func updateLights() {
        let active = UIApplication.shared.applicationState == .active
        serverLamp.set(networkUp && client.configured && !horseID.isEmpty)
        workLamp.set(networkUp && active && UIApplication.shared.isIdleTimerDisabled && !planID.isEmpty && !latestPaused)
        learnLamp.set(networkUp && active && !planID.isEmpty && (!latestPaused || !completedSources.isEmpty))
    }

    private func updateBattery() {
        if let p = batteryPercent() { batteryLabel.text = "BAT (p)%" }
        else { batteryLabel.text = "BAT --%" }
    }

    private func updateProgress() {
        let hours = Int(shiftWatchSeconds) / 3600
        let mins = (Int(shiftWatchSeconds) % 3600) / 60
        let item = playlist.isEmpty ? 0 : min(index + 1, playlist.count)
        progressLabel.text = String(format: "%d:%02d / 6:00 · VIDEO %d/%d", hours, mins, item, playlist.count)
    }

    private func deviceProfile() -> [String: Any] {
        let memoryMB = Int(ProcessInfo.processInfo.physicalMemory / (1024 * 1024))
        var profile: [String: Any] = [
            "platform": "ios",
            "platform_version": UIDevice.current.systemVersion,
            "device_class": UIDevice.current.userInterfaceIdiom == .pad ? "ipad" : "mobile",
            "model_family": machineIdentifier(),
            "memory_mb": memoryMB,
            "cpu_cores": ProcessInfo.processInfo.processorCount,
            "free_storage_gb": Double(freeDiskBytes()) / 1_073_741_824.0,
            "charging": UIDevice.current.batteryState == .charging || UIDevice.current.batteryState == .full,
            "thermal_state": thermalName(ProcessInfo.processInfo.thermalState),
            "browser_available": true,
            "video_playback": true,
            "screen_understanding": true,
            "transcript_capable": false,
            "playwright_available": false,
            "yt_dlp_available": false,
            "network_online": networkUp,
            "serial_collected": false,
            "mac_address_collected": false,
        ]
        if let battery = batteryPercent() { profile["battery_percent"] = battery }
        return profile
    }

    private func persistLocalBatch() {
        defaults.set(planID, forKey: "horse.plan.id")
        defaults.set(subject, forKey: "horse.plan.subject")
        defaults.set(index, forKey: "horse.plan.index")
        defaults.set(shiftStartedAt, forKey: "horse.shift.started")
        defaults.set(shiftWatchSeconds, forKey: "horse.shift.watch")
        if let data = try? JSONSerialization.data(withJSONObject: completedSources) {
            defaults.set(data, forKey: "horse.sources")
        }
    }

    private func restoreLocalBatch() {
        planID = defaults.string(forKey: "horse.plan.id") ?? ""
        subject = defaults.string(forKey: "horse.plan.subject") ?? ""
        index = defaults.integer(forKey: "horse.plan.index")
        shiftStartedAt = defaults.double(forKey: "horse.shift.started")
        shiftWatchSeconds = defaults.double(forKey: "horse.shift.watch")
        if let data = defaults.data(forKey: "horse.sources"),
           let rows = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]] {
            completedSources = rows
        }
    }

    private func clearTransientBatch() {
        completedSources.removeAll()
        transcriptChunks.removeAll()
        shiftWatchSeconds = 0
        shiftStartedAt = 0
        latestTime = 0
        latestDuration = 0
        priorVideoTime = 0
        defaults.removeObject(forKey: "horse.sources")
        defaults.removeObject(forKey: "horse.shift.watch")
        defaults.removeObject(forKey: "horse.shift.started")
        defaults.removeObject(forKey: "horse.plan.index")
        defaults.removeObject(forKey: "horse.plan.id")
        defaults.removeObject(forKey: "horse.plan.subject")
    }

    @objc private func configureCore() {
        let a = UIAlertController(
            title: "Connect SURYADEV to KRISHNA Core",
            message: "Enter your trusted private KRISHNA Core address once. Pairing still requires approval on the KRISHNA PC.",
            preferredStyle: .alert
        )
        a.addTextField { field in
            field.placeholder = "http://192.168.x.x:8766"
            field.text = self.client.baseURL
            field.keyboardType = .URL
            field.autocapitalizationType = .none
        }
        a.addAction(UIAlertAction(title: "Save & Pair", style: .default) { [weak self, weak a] _ in
            guard let self else { return }
            self.client.baseURL = a?.textFields?.first?.text ?? ""
            guard self.client.configured else { return }
            self.client.requestPairing { [weak self] code, _ in
                DispatchQueue.main.async {
                    if code == 200 {
                        self?.show("Pairing requested", "Approve this Node ID on KRISHNA PC:\n\n(self?.client.deviceID ?? "")\n\nThen tap CURRICULUM or reopen the app.")
                    } else {
                        self?.show("Pairing failed", "Check the private Core address and Wi-Fi.")
                    }
                }
            }
        })
        a.addAction(UIAlertAction(title: "Cancel", style: .cancel))
        present(a, animated: true)
    }

    private func show(_ title: String, _ message: String) {
        let a = UIAlertController(title: title, message: message, preferredStyle: .alert)
        a.addAction(UIAlertAction(title: "OK", style: .default))
        present(a, animated: true)
    }

    private func isYouTube(_ raw: String) -> Bool {
        guard let u = URL(string: raw), let h = u.host?.lowercased() else { return false }
        return h == "youtu.be" || h == "youtube.com" || h.hasSuffix(".youtube.com")
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard action.targetFrame?.isMainFrame ?? true else { decisionHandler(.allow); return }
        guard let url = action.request.url, let host = url.host?.lowercased() else {
            decisionHandler(.cancel); return
        }
        let ok = host == "youtu.be" || host == "youtube.com" || host.hasSuffix(".youtube.com")
            || host == "google.com" || host.hasSuffix(".google.com")
        decisionHandler(ok ? .allow : .cancel)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { sampleVideo() }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        workLamp.set(false)
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        workLamp.set(false)
    }
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        workLamp.set(false); learnLamp.set(false)
        persistLocalBatch()
        webView.reload()
    }

    private func batteryPercent() -> Int? {
        let level = UIDevice.current.batteryLevel
        guard level >= 0 else { return nil }
        return Int((level * 100).rounded())
    }

    private func freeDiskBytes() -> Int64 {
        let values = try? URL(fileURLWithPath: NSHomeDirectory())
            .resourceValues(forKeys: [.volumeAvailableCapacityForImportantUsageKey])
        return values?.volumeAvailableCapacityForImportantUsage ?? 0
    }

    private func machineIdentifier() -> String {
        var info = utsname(); uname(&info)
        return Mirror(reflecting: info.machine).children.reduce("") { out, child in
            guard let v = child.value as? Int8, v != 0 else { return out }
            return out + String(UnicodeScalar(UInt8(v)))
        }
    }

    private func thermalName(_ state: ProcessInfo.ThermalState) -> String {
        switch state {
        case .nominal: return "nominal"
        case .fair: return "fair"
        case .serious: return "serious"
        case .critical: return "critical"
        @unknown default: return "unknown"
        }
    }
}
