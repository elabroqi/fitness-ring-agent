import Foundation

final class APIClient {
    static let shared = APIClient()
    
    private init() {}
    
    // Simulator:
    private let baseURL = "http://127.0.0.1:8000"
    
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
}