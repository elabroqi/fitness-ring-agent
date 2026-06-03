import SwiftUI

struct ContentView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem {
                    Label("Dashboard", systemImage: "house.fill")
                }

            RewardsView()
                .tabItem {
                    Label("Rewards", systemImage: "gift.fill")
                }

            RingView()
                .tabItem {
                    Label("Ring", systemImage: "dot.radiowaves.left.and.right")
                }

            AgentChatView()
                .tabItem {
                    Label("Agent", systemImage: "message.fill")
                }
        }
    }
}

#Preview {
    ContentView()
}
