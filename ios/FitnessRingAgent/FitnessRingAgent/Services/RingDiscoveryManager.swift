import Foundation
import CoreBluetooth

struct DiscoveredRing: Identifiable {
    let id: UUID
    let name: String
    let rssi: Int
}

final class RingDiscoveryManager: NSObject, ObservableObject {
    @Published var discoveredRings: [DiscoveredRing] = []
    @Published var isScanning = false
    @Published var bluetoothState = "Unknown"

    private var centralManager: CBCentralManager!

    private let supportedPrefixes = [
        "R01", "R02", "R03", "R04", "R05", "R06", "R07", "R09", "R10",
        "R20", "COLMI", "Hello Ring", "TR-R02"
    ]

    override init() {
        super.init()
        centralManager = CBCentralManager(delegate: self, queue: nil)
    }

    func startScan() {
        guard centralManager.state == .poweredOn else {
            return
        }

        discoveredRings.removeAll()
        isScanning = true

        centralManager.scanForPeripherals(
            withServices: nil,
            options: [CBCentralManagerScanOptionAllowDuplicatesKey: false]
        )

        DispatchQueue.main.asyncAfter(deadline: .now() + 10) {
            self.stopScan()
        }
    }

    func stopScan() {
        centralManager.stopScan()
        isScanning = false
    }
}

extension RingDiscoveryManager: CBCentralManagerDelegate {
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        switch central.state {
        case .poweredOn:
            bluetoothState = "On"
        case .poweredOff:
            bluetoothState = "Off"
        case .unauthorized:
            bluetoothState = "Unauthorized"
        case .unsupported:
            bluetoothState = "Unsupported"
        default:
            bluetoothState = "Unavailable"
        }
    }

    func centralManager(
        _ central: CBCentralManager,
        didDiscover peripheral: CBPeripheral,
        advertisementData: [String: Any],
        rssi RSSI: NSNumber
    ) {
        let name = peripheral.name
            ?? advertisementData[CBAdvertisementDataLocalNameKey] as? String
            ?? ""

        guard supportedPrefixes.contains(where: { name.hasPrefix($0) }) else {
            return
        }

        let ring = DiscoveredRing(
            id: peripheral.identifier,
            name: name,
            rssi: RSSI.intValue
        )

        if !discoveredRings.contains(where: { $0.id == ring.id }) {
            discoveredRings.append(ring)
        }
    }
}