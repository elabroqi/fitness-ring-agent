import SwiftUI
import CoreBluetooth 

struct DeviceBindingView: View {
    @AppStorage("user_id") private var userId: String = ""

    @StateObject private var discoveryManager = RingDiscoveryManager()
    @State private var isSubmitting = false
    @State private var bindingStatusMessage = ""
    
    @State private var isRequestingBluetooth = false
    @State private var showBluetoothDeniedAlert = false

    var body: some View {
        VStack(spacing: 20) {
            Text("Select Wearable Interface")
                .font(.title2)
                .fontWeight(.bold)

            Button(discoveryManager.isScanning ? "Scanning..." : "Scan") {
                discoveryManager.startScan()
            }
            .buttonStyle(.borderedProminent)

            List(discoveryManager.discoveredRings) { ring in
                HStack {
                    VStack(alignment: .leading) {
                        Text(ring.name)
                            .font(.headline)

                        Text("Signal: \(ring.rssi)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    Button("Bind") {
                        isRequestingBluetooth = true
                        Task { @MainActor in
                            let status = await BluetoothPermissionManager.shared.requestAuthorization()
                            isRequestingBluetooth = false
                            switch status {
                            case .allowedAlways:
                                // Proceed with your ring discovery/bind flow
                                startBindingFlow()
                            case .restricted, .denied:
                                // Guide the user to Settings if needed
                                showBluetoothDeniedAlert = true
                            case .notDetermined:
                                // Rare edge case — consider retrying or informing the user
                                break
                            @unknown default:
                                break
                            }
                        }
                    }
                    .disabled(isRequestingBluetooth)
                    .alert("Bluetooth Access Needed",
                           isPresented: $showBluetoothDeniedAlert,
                           actions: {
                               Button("OK", role: .cancel) { }
                           },
                           message: {
                               Text("Please enable Bluetooth access in Settings to bind your ring.")
                           }
                    )
                }
            }

            if !bindingStatusMessage.isEmpty {
                Text(bindingStatusMessage)
                    .font(.caption)
                    .foregroundColor(.blue)
            }
        }
        .padding()
        .onDisappear {
            discoveryManager.stopScan()
        }
    }

    private func bindSelectedDevice(ring: DiscoveredRing) async {
        isSubmitting = true
        bindingStatusMessage = "Binding device..."

        do {
            try await APIClient.shared.bindDevice(
                userId: userId,
                deviceName: ring.name,
                peripheralUUID: ring.id.uuidString,
                deviceType: ring.name
            )

            bindingStatusMessage = "Device bound successfully."
            discoveryManager.stopScan()
        } catch {
            bindingStatusMessage = "Could not bind device."
        }

        isSubmitting = false
    }
}


@IBAction func bindRingTapped(_ sender: Any) {
    Task { @MainActor in
        let status = await BluetoothPermissionManager.shared.requestAuthorization()
        switch status {
        case .allowedAlways:
            startBindingFlow()
        case .restricted, .denied:
            presentDeniedAlert() // Show guidance to enable Bluetooth in Settings
        case .notDetermined:
            break
        @unknown default:
            break
        }
    }
}
