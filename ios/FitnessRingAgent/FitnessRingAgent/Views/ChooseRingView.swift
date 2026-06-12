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
                // Aligned with the robust scanning method name we created earlier
                discoveryManager.startScan()
            }
            .buttonStyle(.borderedProminent)
            .disabled(discoveryManager.isScanning)

            List(discoveryManager.discoveredRings) { ring in
                HStack {
                    VStack(alignment: .leading) {
                        Text(ring.name)
                            .font(.headline)

                        Text("Signal: \(ring.rssi) dBm")
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
                                // Pass the selected list item straight into your binding loop execution sequence
                                await bindSelectedDevice(ring: ring)
                            case .restricted, .denied:
                                showBluetoothDeniedAlert = true
                            case .notDetermined:
                                break
                            @unknown default:
                                break
                            }
                        }
                    }
                    .disabled(isRequestingBluetooth || isSubmitting)
                }
            }
            .alert("Bluetooth Access Needed", isPresented: $showBluetoothDeniedAlert) {
                Button("OK", role: .cancel) { }
            } message: {
                Text("Please enable Bluetooth access in Settings to bind your ring.")
            }

            if isSubmitting {
                ProgressView()
            }

            if !bindingStatusMessage.isEmpty {
                Text(bindingStatusMessage)
                    .font(.subheadline)
                    .foregroundColor(bindingStatusMessage.contains("successfully") ? .green : .blue)
                    .bold()
            }
        }
        .padding()
        .onDisappear {
            // Safely clean up radio hardware cycles when navigating away
            discoveryManager.stopScan()
        }
    }

    private func bindSelectedDevice(ring: DiscoveredRing) async {
        isSubmitting = true
        bindingStatusMessage = "Binding device..."

        do {
            // Hits your newly updated APIClient with identical key alignments!
            try await APIClient.shared.bindDevice(
                userId: userId,
                deviceName: ring.name,
                peripheralUUID: ring.id.uuidString,
                deviceType: ring.name
            )

            bindingStatusMessage = "Device bound successfully."
            discoveryManager.stopScan()
        } catch {
            print("❌ Device registration network write skipped: \(error)")
            bindingStatusMessage = "Could not bind device."
        }

        isSubmitting = false
    }
}