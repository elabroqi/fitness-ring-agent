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
                    // Optimized status message showing the live BLE hardware pipeline status
                    if isLoading {
                        ProgressView("Syncing with ring over BLE...")
                            .padding()
                    }
                    
                    if let errorMessage {
                        Text(errorMessage)
                            .foregroundStyle(.red)
                            .font(.subheadline)
                            .padding()
                    }
                    
                    if let dashboard {
                        MetricCard(title: "Steps", value: "\(dashboard.steps)", icon: "figure.walk")
                        MetricCard(title: "Heart Rate", value: "\(dashboard.bpm) bpm", icon: "heart.fill")
                        MetricCard(title: "SpO₂", value: "\(dashboard.spo2)%", icon: "drop.fill")
                        MetricCard(title: "Stress", value: "\(dashboard.stressScore)", icon: "brain.head.profile")
                        MetricCard(title: "Calories", value: String(format: "%.0f kcal", dashboard.calories), icon: "flame.fill")
                        
                        if let reward = dashboard.latestReward {
                            MetricCard(title: "Latest Reward", value: "\(reward.tier): \(reward.rewardDescription)", icon: "gift.fill")
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("Welcome \(userId)")
            // 🚀 Runs instantly when dashboard page loads up
            .task {
                await loadDashboard()
            }
            // 🔄 Triggers script when user performs a manual pull-to-refresh pull down
            .refreshable {
                await loadDashboard()
            }
        }
    }
    
    func loadDashboard() async {
        // Enforce state mutations cleanly back on the primary Main UI Thread 
        DispatchQueue.main.async {
            self.isLoading = true
            self.errorMessage = nil
        }
        
        do {
            // Hits your newly automated FastAPI background subprocess trigger endpoint node!
            let freshData = try await APIClient.shared.fetchDashboard(userId: userId)
            
            DispatchQueue.main.async {
                self.dashboard = freshData
                self.isLoading = false
            }
        } catch {
            print("❌ Dashboard network data sync failure pipeline: \(error)")
            DispatchQueue.main.async {
                self.errorMessage = "Could not load dashboard data."
                self.isLoading = false
            }
        }
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