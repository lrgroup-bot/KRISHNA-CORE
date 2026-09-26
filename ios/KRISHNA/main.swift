import UIKit
import AVFoundation
import Photos
import Speech
import CoreImage

@main
final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let w = UIWindow(frame: UIScreen.main.bounds)
        w.rootViewController = MainViewController()
        w.makeKeyAndVisible()
        window = w
        return true
    }
}

final class MainViewController: UIViewController, SFSpeechRecognizerDelegate {
    private let avatar = UIImageView()
    private let status = UILabel()
    private let audioEngine = AVAudioEngine()
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private var recognizer = SFSpeechRecognizer(locale: Locale(identifier: "or-IN"))

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 0.01, green: 0.04, blue: 0.08, alpha: 1)

        avatar.translatesAutoresizingMaskIntoConstraints = false
        avatar.contentMode = .scaleAspectFit
        if let url = Bundle.main.url(forResource: "krishna_child_360", withExtension: "webp"),
           let data = try? Data(contentsOf: url) {
            avatar.image = UIImage(data: data)
        }
        view.addSubview(avatar)

        status.translatesAutoresizingMaskIntoConstraints = false
        status.text = "KRISHNA"
        status.textColor = UIColor(red: 0.95, green: 0.80, blue: 0.42, alpha: 1)
        status.font = .systemFont(ofSize: 13, weight: .semibold)
        status.textAlignment = .center
        view.addSubview(status)

        let hawkeye = roundButton("◉", action: #selector(openHawkeye))
        hawkeye.accessibilityLabel = "Open Hawkeye"
        let chat = roundButton("⌁", action: #selector(openChat))
        chat.accessibilityLabel = "Open chat"
        let mic = roundButton("🎙", action: #selector(toggleMic))
        mic.accessibilityLabel = "Talk to KRISHNA"

        let dock = UIStackView(arrangedSubviews: [hawkeye, chat, mic])
        dock.translatesAutoresizingMaskIntoConstraints = false
        dock.axis = .horizontal
        dock.spacing = 14
        dock.alignment = .center
        dock.distribution = .equalCentering
        view.addSubview(dock)

        NSLayoutConstraint.activate([
            avatar.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            avatar.centerYAnchor.constraint(equalTo: view.centerYAnchor, constant: -10),
            avatar.widthAnchor.constraint(equalTo: view.widthAnchor, multiplier: 0.82),
            avatar.heightAnchor.constraint(equalTo: view.heightAnchor, multiplier: 0.73),
            status.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            status.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 8),
            dock.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            dock.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -12)
        ])
    }

    private func roundButton(_ title: String, action: Selector) -> UIButton {
        let b = UIButton(type: .system)
        b.translatesAutoresizingMaskIntoConstraints = false
        b.setTitle(title, for: .normal)
        b.titleLabel?.font = .systemFont(ofSize: 19, weight: .semibold)
        b.tintColor = .white
        b.setTitleColor(.white, for: .normal)
        b.backgroundColor = UIColor(red: 0.03, green: 0.15, blue: 0.22, alpha: 0.95)
        b.layer.borderWidth = 1
        b.layer.borderColor = UIColor(red: 0.32, green: 0.82, blue: 0.92, alpha: 0.55).cgColor
        b.layer.cornerRadius = 23
        b.widthAnchor.constraint(equalToConstant: 46).isActive = true
        b.heightAnchor.constraint(equalToConstant: 46).isActive = true
        b.addTarget(self, action: action, for: .touchUpInside)
        return b
    }

    @objc private func openHawkeye() {
        present(CameraViewController(photographer: false), animated: true)
    }

    @objc private func openChat() {
        let alert = UIAlertController(title: "KRISHNA", message: "Conversation shell. PC pairing remains the authority for full KRISHNA project control.", preferredStyle: .alert)
        alert.addTextField { $0.placeholder = "Talk to KRISHNA…" }
        alert.addAction(UIAlertAction(title: "Send", style: .default) { [weak self, weak alert] _ in
            let text = alert?.textFields?.first?.text?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            if !text.isEmpty { self?.status.text = "KRISHNA · " + text.prefix(24) }
        })
        alert.addAction(UIAlertAction(title: "Close", style: .cancel))
        present(alert, animated: true)
    }

    @objc private func toggleMic() {
        if audioEngine.isRunning { stopListening(); return }
        SFSpeechRecognizer.requestAuthorization { [weak self] auth in
            guard auth == .authorized else { return }
            AVAudioSession.sharedInstance().requestRecordPermission { ok in
                guard ok else { return }
                DispatchQueue.main.async { self?.startListening() }
            }
        }
    }

    private func startListening() {
        recognitionTask?.cancel()
        recognitionTask = nil
        recognizer = SFSpeechRecognizer(locale: Locale(identifier: "or-IN"))
        recognizer?.delegate = self
        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults = true
        recognitionRequest = req
        let input = audioEngine.inputNode
        let format = input.outputFormat(forBus: 0)
        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in req.append(buffer) }
        do {
            try AVAudioSession.sharedInstance().setCategory(.record, mode: .measurement, options: .duckOthers)
            try AVAudioSession.sharedInstance().setActive(true, options: .notifyOthersOnDeactivation)
            audioEngine.prepare()
            try audioEngine.start()
            status.text = "KRISHNA · LISTENING"
        } catch { return }
        recognitionTask = recognizer?.recognitionTask(with: req) { [weak self] result, error in
            guard let self else { return }
            if let text = result?.bestTranscription.formattedString {
                self.status.text = "KRISHNA · " + String(text.prefix(28))
                if result?.isFinal == true {
                    self.routeVoice(text)
                    self.stopListening()
                }
            }
            if error != nil { self.stopListening() }
        }
    }

    private func routeVoice(_ raw: String) {
        let s = raw.lowercased()
        if s.contains("dekh") || s.contains("देख") || s.contains("ଦେଖ") || s.contains("watch") || s.contains("see") || s.contains("look") || s.contains("hawkeye") {
            present(CameraViewController(photographer: false), animated: true)
        } else if s.contains("photo") || s.contains("picture") || s.contains("selfie") || s.contains("फोटो") || s.contains("ଫଟୋ") {
            present(CameraViewController(photographer: true), animated: true)
        }
    }

    private func stopListening() {
        if audioEngine.isRunning { audioEngine.stop() }
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()
        recognitionRequest = nil
        recognitionTask = nil
        status.text = "KRISHNA"
    }
}

final class CameraViewController: UIViewController, AVCapturePhotoCaptureDelegate {
    private let session = AVCaptureSession()
    private let output = AVCapturePhotoOutput()
    private var preview: AVCaptureVideoPreviewLayer!
    private var currentPosition: AVCaptureDevice.Position
    private let photographer: Bool
    private let ciContext = CIContext()

    init(photographer: Bool) {
        self.photographer = photographer
        self.currentPosition = photographer ? .front : .back
        super.init(nibName: nil, bundle: nil)
        modalPresentationStyle = .fullScreen
    }
    required init?(coder: NSCoder) { fatalError() }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        preview = AVCaptureVideoPreviewLayer(session: session)
        preview.videoGravity = .resizeAspectFill
        preview.frame = view.bounds
        view.layer.addSublayer(preview)

        let close = actionButton("×", #selector(closeCamera))
        let flip = actionButton("↺", #selector(flipCamera))
        let shutter = actionButton("", #selector(capture))
        shutter.backgroundColor = UIColor.white.withAlphaComponent(0.24)
        shutter.layer.borderWidth = 4
        shutter.layer.borderColor = UIColor.white.cgColor
        shutter.layer.cornerRadius = 31
        shutter.widthAnchor.constraint(equalToConstant: 62).isActive = true
        shutter.heightAnchor.constraint(equalToConstant: 62).isActive = true

        let more = actionButton("⋯", #selector(showMore))
        [close, flip, shutter, more].forEach { view.addSubview($0) }
        NSLayoutConstraint.activate([
            close.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 8),
            close.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -14),
            flip.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -18),
            flip.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 24),
            shutter.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -12),
            shutter.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            more.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -18),
            more.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -24)
        ])

        requestCameraAndStart()
        if photographer {
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.4) { [weak self] in self?.capture() }
        }
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        preview?.frame = view.bounds
    }

    private func actionButton(_ title: String, _ action: Selector) -> UIButton {
        let b = UIButton(type: .system)
        b.translatesAutoresizingMaskIntoConstraints = false
        b.setTitle(title, for: .normal)
        b.titleLabel?.font = .systemFont(ofSize: 26, weight: .medium)
        b.setTitleColor(.white, for: .normal)
        b.backgroundColor = UIColor.black.withAlphaComponent(0.45)
        b.layer.cornerRadius = 23
        b.widthAnchor.constraint(equalToConstant: 46).isActive = true
        b.heightAnchor.constraint(equalToConstant: 46).isActive = true
        b.addTarget(self, action: action, for: .touchUpInside)
        return b
    }

    private func requestCameraAndStart() {
        AVCaptureDevice.requestAccess(for: .video) { [weak self] ok in
            guard ok else { return }
            DispatchQueue.global(qos: .userInitiated).async { self?.configureSession() }
        }
    }

    private func camera(_ position: AVCaptureDevice.Position) -> AVCaptureDevice? {
        AVCaptureDevice.DiscoverySession(deviceTypes: [.builtInWideAngleCamera, .builtInUltraWideCamera, .builtInTelephotoCamera], mediaType: .video, position: position).devices.first
    }

    private func configureSession() {
        session.beginConfiguration()
        session.sessionPreset = .photo
        for input in session.inputs { session.removeInput(input) }
        guard let device = camera(currentPosition), let input = try? AVCaptureDeviceInput(device: device), session.canAddInput(input) else {
            session.commitConfiguration(); return
        }
        session.addInput(input)
        if session.outputs.isEmpty && session.canAddOutput(output) { session.addOutput(output) }
        session.commitConfiguration()
        session.startRunning()
    }

    @objc private func capture() {
        let settings = AVCapturePhotoSettings()
        settings.photoQualityPrioritization = .quality
        output.capturePhoto(with: settings, delegate: self)
    }

    @objc private func flipCamera() {
        currentPosition = currentPosition == .front ? .back : .front
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in self?.configureSession() }
    }

    @objc private func closeCamera() {
        session.stopRunning()
        dismiss(animated: true)
    }

    @objc private func showMore() {
        let alert = UIAlertController(title: "HAWKEYE", message: "Advanced diagnostics remain available through the KRISHNA PC/mobile HAWKEYE pipeline. iOS keeps the camera surface uncluttered.", preferredStyle: .actionSheet)
        alert.addAction(UIAlertAction(title: "Close", style: .cancel))
        present(alert, animated: true)
    }

    func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        guard error == nil, let data = photo.fileDataRepresentation() else { return }
        let finalData = photographer ? naturalEdit(data) : data
        PHPhotoLibrary.requestAuthorization(for: .addOnly) { auth in
            guard auth == .authorized || auth == .limited else { return }
            PHPhotoLibrary.shared().performChanges({
                let request = PHAssetCreationRequest.forAsset()
                request.addResource(with: .photo, data: finalData, options: nil)
            })
        }
    }

    private func naturalEdit(_ data: Data) -> Data {
        guard let input = CIImage(data: data) else { return data }
        let controls = CIFilter(name: "CIColorControls")!
        controls.setValue(input, forKey: kCIInputImageKey)
        controls.setValue(1.06, forKey: kCIInputContrastKey)
        controls.setValue(1.07, forKey: kCIInputSaturationKey)
        controls.setValue(0.02, forKey: kCIInputBrightnessKey)
        guard let out = controls.outputImage,
              let cg = ciContext.createCGImage(out, from: out.extent) else { return data }
        return UIImage(cgImage: cg).jpegData(compressionQuality: 0.94) ?? data
    }
}
