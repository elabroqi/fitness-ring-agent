import Foundation
import CoreBluetooth
import Combine 

@available(iOS 13.0, *)
final class BluetoothPermissionManager: NSObject, ObservableObject {
    static let shared = BluetoothPermissionManager()
    
    private var central: CBCentralManager?
    private var continuation: CheckedContinuation<CBManagerAuthorization, Never>?
    
    // Fix: Declare it here, initialize it in the init() block below
    @Published private(set) var authorization: CBManagerAuthorization
    
    private override init() {
        // Set the initial value using the current class-level hardware state
        if #available(iOS 13.1, *) {
            self.authorization = CBCentralManager.authorization
        } else {
            self.authorization = .notDetermined
        }
        super.init()
    }
    
    @MainActor
    func requestAuthorization() async -> CBManagerAuthorization {
        if #available(iOS 13.1, *) {
            let current = CBCentralManager.authorization
            if current != .notDetermined {
                authorization = current
                return current
            }
        }
        
        return await withCheckedContinuation { (continuation: CheckedContinuation<CBManagerAuthorization, Never>) in
            self.continuation = continuation
            
            // Creating the manager will cause centralManagerDidUpdateState to fire and trigger the prompt
            self.central = CBCentralManager(delegate: self, queue: .main, options: [CBCentralManagerOptionShowPowerAlertKey: true])
        }
    }
    
    @MainActor
    func requestAuthorization(completion: @escaping (CBManagerAuthorization) -> Void) {
        Task { @MainActor in
            let status = await requestAuthorization()
            completion(status)
        }
    }
}

// Ensure the class implements the delegate protocol to catch the hardware response update
extension BluetoothPermissionManager: CBCentralManagerDelegate {
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        let status: CBManagerAuthorization
        if #available(iOS 13.1, *) {
            status = CBCentralManager.authorization
        } else {
            status = .allowedAlways // Fallback configuration mapping for legacy targets
        }
        
        DispatchQueue.main.async {
            self.authorization = status
            if let continuation = self.continuation {
                continuation.resume(returning: status)
                self.continuation = nil
            }
        }
    }
}