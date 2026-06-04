import SwiftUI

struct ContentView: View {
    @AppStorage("hasSeenWelcome") private var hasSeenWelcome: Bool = false

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

            AccountView()
                .tabItem {
                    Label("Account", systemImage: "person.crop.circle")
                }
        }
        .fullScreenCover(isPresented: .constant(!hasSeenWelcome)) {
            WelcomeView(hasSeenWelcome: $hasSeenWelcome)
        }
    }
}

struct AccountView: View {
    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Image(systemName: "person.crop.circle.fill")
                    .font(.system(size: 64))
                    .foregroundStyle(.secondary)
                Text("Account")
                    .font(.title2)
                    .bold()
                Text("Manage your profile and settings here.")
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding()
            .navigationTitle("Account")
        }
    }
}

struct WelcomeView: View {
    @Binding var hasSeenWelcome: Bool

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            Image(systemName: "sparkles")
                .font(.system(size: 72))
                .foregroundStyle(.tint)
            Text("Welcome")
                .font(.largeTitle).bold()
            Text("Thanks for installing the app! Here's a quick start—tap Continue to jump in.")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .padding(.horizontal)
            Spacer()
            Button {
                hasSeenWelcome = true
            } label: {
                Text("Continue")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .padding(.horizontal)
            .padding(.bottom)
        }
    }
}

#Preview {
    ContentView()
}
