import SwiftUI

struct ContentView: View {
    @AppStorage("user_id") private var userId: String = ""
    
    var body: some View {
        if userId.isEmpty {
            WelcomeView(userId: $userId)
        } else {
            MainTabView()
        }
    }
}

struct MainTabView: View {
    @State private var isPresentingAgent: Bool = false
    
    var body: some View {
        ZStack(alignment: .bottomTrailing) {
            // Core Navigation Subsystem Matrix
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
            .tint(.blue)
            
            #if os(iOS)
            // Floating Intelligence Action Interface Overlay Layer
            Button(action: {
                isPresentingAgent = true
            }) {
                ZStack {
                    Circle()
                        .fill(
                            LinearGradient(
                                colors: [.blue, .purple],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 56, height: 56)
                        .shadow(color: .purple.opacity(0.35), radius: 6, x: 0, y: 3)
                    
                    Image(systemName: "sparkles")
                        .font(.title2)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                }
            }
            .padding(.trailing, 20)
            // Pad upward cleanly to avoid intersection collisions with system TabBar nodes
            .padding(.bottom, 62)
            #endif
        }
        // Asynchronous Sheet Context Target Binding
        .sheet(isPresented: $isPresentingAgent) {
            AgentChatView()
        }
    }
}

struct AccountView: View {
    @AppStorage("user_id") private var userId: String = ""

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Image(systemName: "person.crop.circle.fill")
                    .font(.system(size: 64))
                    .foregroundStyle(.secondary)

                Text("Account")
                    .font(.title2)
                    .bold()

                Text("Logged in as: \(userId)")
                    .foregroundStyle(.secondary)

                Button(role: .destructive) {
                    userId = ""
                } label: {
                    Text("Log Out")
                }
                .buttonStyle(.bordered)
                .padding(.top, 12)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding()
            .navigationTitle("Account")
        }
    }
}

struct WelcomeView: View {
    @Binding var userId: String
    @State private var username: String = ""

    private var trimmedUsername: String {
        username.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "sparkles")
                .font(.system(size: 72))
                .foregroundStyle(.tint)

            Text("Fitness Ring Agent")
                .font(.largeTitle)
                .bold()

            Text("Connect your ring, track your health, and unlock rewards.")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .padding(.horizontal)

            TextField("Enter username", text: $username)
                .textFieldStyle(.roundedBorder)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .padding(.horizontal)

            Spacer()

            Button {
                userId = trimmedUsername
            } label: {
                Text("Continue")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(trimmedUsername.isEmpty)
            .padding(.horizontal)
            .padding(.bottom)
        }
        .padding()
    }
}

#Preview {
    ContentView()
}