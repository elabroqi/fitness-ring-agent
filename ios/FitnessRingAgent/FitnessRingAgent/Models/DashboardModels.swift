import Foundation

struct DashboardResponse: Codable {
    let userId: String
    let date: String?

    let connectedDeviceName: String
    let batteryLevel: Float
    let deviceType: String?

    let steps: Float
    let distanceMeters: Float
    let activeMinutes: Float
    let calories: Float

    let bpm: Float
    let spo2: Float
    let stressScore: Float

    let latestReward: Reward?

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case date
        case connectedDeviceName = "connected_device_name"
        case batteryLevel = "battery_level"
        case deviceType = "device_type"
        case steps
        case distanceMeters = "distance_meters"
        case activeMinutes = "active_minutes"
        case calories
        case bpm
        case spo2
        case stressScore = "stress_score"
        case latestReward = "latest_reward"
    }
}

struct Reward: Codable {
    let brand: String
    let tier: String
    let description: String
    let unlockedAt: String?
    let used: Bool

    enum CodingKeys: String, CodingKey {
        case brand
        case tier
        case description
        case unlockedAt = "unlocked_at"
        case used
    }
}

struct ChatResponse: Codable {
    let reply: String
}
