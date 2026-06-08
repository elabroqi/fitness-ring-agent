import SwiftUI

struct DashboardView: View {
    @AppStorage("user_id") private var userId: String = ""
    @State private var dashboard: DashboardResponse?
    @State private var isLoading = false
    @State private var errorMessage: String?
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    if isLoading {
                        ProgressView("Loading dashboard...")
                    }
                    
                    if let errorMessage {
                        Text(errorMessage)
                            .foregroundStyle(.red)
                    }
                    
                    if let dashboard {
                        MetricCard(title: "Steps", value: "\(dashboard.steps)", icon: "figure.walk")
                        MetricCard(title: "Heart Rate", value: "\(dashboard.bpm) bpm", icon: "heart.fill")
                        MetricCard(title: "SpO₂", value: "\(dashboard.spo2)%", icon: "drop.fill")
                        MetricCard(title: "Stress", value: "\(dashboard.stressScore)", icon: "brain.head.profile")
                        MetricCard(title: "Calories", value: "\(dashboard.calories)", icon: "flame.fill")
                        
                        if let reward = dashboard.latestReward {
                            MetricCard(title: "Latest Reward", value: "\(reward.tier): \(reward.description)", icon: "gift.fill")
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("Halo AI")
            .task {
                await loadDashboard()
            }
            .refreshable {
                await loadDashboard()
            }
        }
    }
    
    func loadDashboard() async {
        isLoading = true
        errorMessage = nil
        
        do {
            dashboard = try await APIClient.shared.fetchDashboard(userId: userId)
        } catch {
            errorMessage = "Could not load dashboard data."
        }
        
        isLoading = false
    }
}

struct MetricCard: View {
    let title: String
    let value: String
    let icon: String
    
    var body: some View {
        HStack {
            Image(systemName: icon)
                .font(.title2)
                .frame(width: 36)
            
            VStack(alignment: .leading) {
                Text(title)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(value)
                    .font(.title3)
                    .bold()
            }
            
            Spacer()
        }
        .padding()
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 18))
    }
}