import Foundation

final class APIClient {
    static let shared = APIClient()
    
    private init() {}
    
    private let baseURL = "http://192.168.1.244:8000"
    
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

    func bindDevice(
        userId: String,
        deviceName: String,
        peripheralUUID: String,
        deviceFamily: String
    ) async throws {
        guard let url = URL(string: "\(baseURL)/devices/bind") else {
            throw URLError(.badURL)
        }

        let iso = ISO8601DateFormatter().string(from: Date())

        let payload: [String: String] = [
            "user_id": userId,
            "device_name": deviceName,
            "ios_peripheral_uuid": peripheralUUID,
            "device_family": deviceFamily,
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
}
