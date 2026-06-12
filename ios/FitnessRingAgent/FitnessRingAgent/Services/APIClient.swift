import Foundation

final class APIClient {
    static let shared = APIClient()
    
    private init() {}
    
    // Explicitly targets your laptop's local development network interface
    private let baseURL = "https://cova.onrender.com"
    
    // =============================================================================
    // 📊 METRIC & TELEMETRY FETCH PATHS
    // =============================================================================
    
    func fetchDashboard(userId: String) async throws -> DashboardResponse {
        guard let url = URL(string: "\(baseURL)/dashboard/\(userId)") else {
            throw URLError(.badURL)
        }

        let (data, response) = try await URLSession.shared.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse,
              200..<300 ~= httpResponse.statusCode else {
            throw URLError(.badServerResponse)
        }

        return try JSONDecoder().decode(DashboardResponse.self, from: data)
    }

    // =============================================================================
    // 🔒 HARDWARE PROVISIONING & BINDING PATHS
    // =============================================================================

    func bindDevice(
        userId: String,
        deviceName: String,
        peripheralUUID: String,
        deviceType: String
    ) async throws {
        guard let url = URL(string: "\(baseURL)/devices/bind") else {
            throw URLError(.badURL)
        }

        let iso = ISO8601DateFormatter().string(from: Date())

        let payload: [String: String] = [
            "user_id": userId,
            "device_name": deviceName,
            "ios_peripheral_uuid": peripheralUUID,
            "device_type": deviceType,
            "bound_at": iso
        ]

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              200..<300 ~= httpResponse.statusCode else {
            throw URLError(.badServerResponse)
        }
    }
    
    func unbindDevice(userId: String) async throws {
        guard let url = URL(string: "\(baseURL)/devices/unbind") else {
            throw URLError(.badURL)
        }
        let payload: [String: String] = ["user_id": userId]
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (_, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, 200..<300 ~= httpResponse.statusCode else {
            throw URLError(.badServerResponse)
        }
    }
    
    // =============================================================================
    // 🤖 NEW: COGNITIVE AI AGENT INTERFACE (Gemini Gateway)
    // =============================================================================
    
    func sendAgentChatMessage(userId: String, message: String) async throws -> String {
        guard let url = URL(string: "\(baseURL)/agent/chat") else {
            throw URLError(.badURL)
        }
        
        let payload: [String: String] = [
            "user_id": userId,
            "message": message
        ]
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse, 
              200..<300 ~= httpResponse.statusCode else {
            throw URLError(.badServerResponse)
        }
        
        // Local structural parsing struct to unpack the response string block cleanly
        struct AgentResponse: Codable {
            let reply: String
        }
        
        let decodedResponse = try JSONDecoder().decode(AgentResponse.self, from: data)
        return decodedResponse.reply
    }
}