import Foundation
import CoreBluetooth
import CoreLocation
import UserNotifications
import CoreMotion
import AppTrackingTransparency
import AdSupport

final class PermissionManager: NSObject, ObservableObject, CLLocationManagerDelegate {
    private let locationManager = CLLocationManager()
    private var bluetoothManager: CBCentralManager?

    override init() {
        super.init()
        locationManager.delegate = self
    }

    func requestStartupPermissions() {
        requestBluetooth()
        requestNotifications()
        requestLocation()
        requestMotion()
        requestTracking()
    }

    private func requestBluetooth() {
        bluetoothManager = CBCentralManager(delegate: nil, queue: nil)
    }

    private func requestNotifications() {
        UNUserNotificationCenter.current().requestAuthorization(
            options: [.alert, .sound, .badge]
        ) { _, _ in }
    }

    private func requestLocation() {
        locationManager.requestWhenInUseAuthorization()

        // Only use this later if you truly need background location:
        // locationManager.requestAlwaysAuthorization()
    }

    private func requestMotion() {
        if CMMotionActivityManager.isActivityAvailable() {
            let manager = CMMotionActivityManager()
            manager.queryActivityStarting(
                from: Date(),
                to: Date(),
                to: .main
            ) { _, _ in }
        }
    }

    private func requestTracking() {
        if #available(iOS 14, *) {
            ATTrackingManager.requestTrackingAuthorization { _ in }
        }
    }
}