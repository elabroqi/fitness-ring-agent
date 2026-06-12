import Foundation
import CoreBluetooth

@available(iOS 13.0, *)
final class BluetoothPermissionManager: NSObject, ObservableObject {
    static let shared = BluetoothPermissionManager()

    private var central: CBCentralManager?
    private var continuation: CheckedContinuation<CBManagerAuthorization, Never>?

    @Published private(set) var authorization: CBManagerAuthorization = CBCentralManager.authorization

    /// Requests Bluetooth permission by initializing a CBCentralManager and briefly scanning.
    /// Call this from your "Bind Ring" action before starting discovery/connection.
    @MainActor
    func requestAuthorization() async -> CBManagerAuthorization {
        let current = CBCentralManager.authorization
        if current != .notDetermined {
            authorization = current
            return current
        }

        return await withCheckedContinuation { (continuation: CheckedContinuation<CBManagerAuthorization, Never>) in
            self.continuation = continuation
            // Creating the manager will cause centralManagerDidUpdateState to fire.
            // The scan below (started when poweredOn) reliably triggers the system prompt.
            self.central = CBCentralManager(delegate: self, queue: .main, options: [CBCentralManagerOptionShowPowerAlertKey: true])
        }
    }

    /// Convenience wrapper if you prefer a completion handler style.
    @MainActor
    func requestAuthorization(completion: @escaping (CBManagerAuthorization) -> Void) {
        Task { @MainActor in
            let status = await requestAuthorization()
            completion(status)
        }
    }
}

@available(iOS 13.0, *)
extension BluetoothPermissionManager: CBCentralManagerDelegate {
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        authorization = CBCentralManager.authorization

        switch central.state {
        case .poweredOn:
            if CBCentralManager.authorization == .notDetermined {
                // Start a very short scan to force the permission prompt.
                central.scanForPeripherals(withServices: nil, options: nil)
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
                    central.stopScan()
                    self.finishIfDetermined()
                }
            } else {
                finishIfDetermined()
            }
        default:
            // For other states (poweredOff, unauthorized, etc.), finish if we have a determination.
            finishIfDetermined()
        }
    }

    private func finishIfDetermined() {
        let auth = CBCentralManager.authorization
        guard auth != .notDetermined else { return }
        authorization = auth
        if let cont = continuation {
            continuation = nil
            cont.resume(returning: auth)
        }
    }
}
