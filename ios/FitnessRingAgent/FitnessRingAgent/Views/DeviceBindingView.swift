import SwiftUI

// =============================================================================
// UNIFIED DATA ARCHITECTURE SCHEMAS
// =============================================================================

struct DashboardData: Codable {
    let userId: String
    let date: String?
    let steps: Int
    let distanceMeters: Int
    let activeMinutes: Int
    let calories: Float
    let bpm: Int 
    let spo2: Int
    let stressScore: Int
    let latestReward: iOSReward?
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case date
        case steps
        case distanceMeters = "distance_meters"
        case activeMinutes = "active_minutes"
        case calories, bpm, spo2
        case stressScore = "stress_score"
        case latestReward = "latest_reward"
    }
}

struct iOSReward: Codable {
    let brand: String
    let tier: String
    let description: String
    let used: Bool
    let unlockedAt: String?
    
    enum CodingKeys: String, CodingKey {
        case brand, tier, description, used
        case unlockedAt = "unlocked_at"
    }
}

// =============================================================================
// USER INTERFACE SCREEN VIEW
// =============================================================================

struct DeviceBindingView: View {
    @StateObject private var discoveryManager = RingDiscoveryManager()
    @State private var isSubmitting: Bool = false
    @State private var bindingStatusMessage: String = ""
    
    @AppStorage("user_id") private var userId: String = "" // Aligns natively with database profiles
    
    var body: some View {
        VStack(spacing: 20) {
            VStack(alignment: .leading, spacing: 8) {
                Text("Hardware Provisioning")
                    .font(.headline)
                    .foregroundColor(.secondary)
                Text("Select Wearable Interface")
                    .font(.title2)
                    .fontWeight(.bold)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal)
            
            List(discoveryManager.discoveredRings) { ring in
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(ring.localName)
                            .font(.body)
                            .fontWeight(.medium)
                        Text("iOS Address Token: \(ring.id.uuidString.prefix(8))...")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    
                    Button(action: {
                        bindSelectedDevice(ring: ring)
                    }) {
                        Text("Bind")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(.blue)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 6)
                            .background(Color.blue.opacity(0.1))
                            .cornerRadius(8)
                    }
                    .disabled(isSubmitting)
                }
                .padding(.vertical, 4)
            }
            .overlay {
                if discoveryManager.discoveredRings.isEmpty {
                    VStack(spacing: 12) {
                        ProgressView()
                            .tint(.secondary)
                        Text("Searching for compatible hardware protocols...")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                }
            }
            
            if !bindingStatusMessage.isEmpty {
                Text(bindingStatusMessage)
                    .font(.caption)
                    .foregroundColor(.blue)
                    .padding()
            }
        }
        .onAppear {
            discoveryManager.startDiscoveryScan()
        }
        .onDisappear {
            discoveryManager.stopDiscoveryScan()
        }
    }
    
    private func bindSelectedDevice(ring: DiscoveredRing) {
        discoveryManager.stopDiscoveryScan()
        isSubmitting = true
        bindingStatusMessage = "Syncing binding payload..."
        
        // Target your laptop's local area network configuration IP address
        guard let url = URL(string: "http://192.168.1.XX:8000/devices/bind") else { return }
        
        let registrationPayload: [String: Any] = [
            "user_id": userId,
            "device_name": ring.name,
            "ios_peripheral_uuid": ring.id.uuidString,
            "device_family": "COLMI_WEARABLE",
            "bound_at": ISO8601DateFormatter().string(from: Date())
        ]
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: registrationPayload)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            DispatchQueue.main.async {
                isSubmitting = false
                if let error = error {
                    self.bindingStatusMessage = "❌ Network Error: \(error.localizedDescription)"
                    return
                }
                
                if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                    self.bindingStatusMessage = "✅ Success: Wearable linked securely to profile."
                } else {
                    self.bindingStatusMessage = "❌ Server error during schema validation mapping."
                }
            }
        }.resume()
    }
}