import SwiftUI

struct DeviceBindingView: View {
    @AppStorage("user_id") private var userId: String = ""

    @StateObject private var discoveryManager = RingDiscoveryManager()
    @State private var isSubmitting = false
    @State private var bindingStatusMessage = ""

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
                        Task {
                            await bindSelectedDevice(ring: ring)
                        }
                    }
                    .disabled(isSubmitting)
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
