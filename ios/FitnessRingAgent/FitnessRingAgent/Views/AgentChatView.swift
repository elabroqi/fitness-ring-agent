import SwiftUI

struct SuggestedPrompt: Identifiable {
    let id = UUID()
    let displayLabel: String
    let actualPrompt: String
}

struct AgentChatView: View {
    @Environment(\.dismiss) private var dismiss
    
    // Dynamic persistence hook matching the rest of your application stack
    @AppStorage("user_id") private var userId: String = ""
    
    @State private var chatInputText: String = ""
    @State private var chatHistoryList: [(sender: String, message: String)] = [
        ("Agent", "Hello! I am Halo, your intelligent health assistant. Ask me anything about your vitals, milestones, or training indices.")
    ]
    @State private var isAwaitingEngineReply: Bool = false
    
    // Explicit Hackathon Sample Question Data Vectors
    private let structuredSuggestions = [
        SuggestedPrompt(displayLabel: "🆚 Friend Comparison", actualPrompt: "How do my steps and workout metrics stack up against my friends this week?"),
        SuggestedPrompt(displayLabel: "🩺 Age Evaluation", actualPrompt: "Based on my active minutes and vitals, how is my health looking for someone my age?"),
        SuggestedPrompt(displayLabel: "🏃‍♂️ Fitness Baselines", actualPrompt: "Are my current heart rate and calorie numbers considered athletic?")
    ]
    
    var body: some View {
        NavigationStack {
            VStack {
                // Conversational Message Log Feed Area
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        ForEach(0..<chatHistoryList.count, id: \.self) { idx in
                            let turn = chatHistoryList[idx]
                            HStack {
                                if turn.sender == "User" { Spacer() }
                                
                                Text(turn.message)
                                    .padding(.horizontal, 16)
                                    .padding(.vertical, 12)
                                    .background(turn.sender == "User" ? Color.blue : Color.gray.opacity(0.15))
                                    .foregroundColor(turn.sender == "User" ? .white : .primary)
                                    .cornerRadius(16)
                                    .frame(maxWidth: 280, alignment: turn.sender == "User" ? .trailing : .leading)
                                
                                if turn.sender == "Agent" { Spacer() }
                            }
                        }
                    }
                    .padding()
                }
                
                // Onboarding Prompt Suggestion Micro-Cards Grid
                if chatHistoryList.count <= 1 {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Suggested Queries")
                            .font(.caption)
                            .fontWeight(.bold)
                            .foregroundColor(.secondary)
                            .padding(.horizontal)
                        
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 10) {
                                ForEach(structuredSuggestions) { option in
                                    Button(action: {
                                        chatInputText = option.actualPrompt
                                    }) {
                                        Text(option.displayLabel)
                                            .font(.subheadline)
                                            .foregroundColor(.primary)
                                            .padding(.horizontal, 14)
                                            .padding(.vertical, 8)
                                            .background(Capsule().stroke(Color.secondary.opacity(0.3)))
                                    }
                                }
                            }
                            .padding(.horizontal)
                        }
                    }
                    .padding(.bottom, 8)
                }
                
                // Interaction Processing Bar Subsystem
                HStack {
                    TextField("Query database indices...", text: $chatInputText)
                        .textFieldStyle(.roundedBorder)
                        .disabled(isAwaitingEngineReply)
                    
                    Button(action: {
                        executeAgentMessageSubmission()
                    }) {
                        if isAwaitingEngineReply {
                            ProgressView()
                        } else {
                            Image(systemName: "paperplane.fill")
                                .foregroundColor(.blue)
                        }
                    }
                    .disabled(chatInputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isAwaitingEngineReply)
                }
                .padding()
                .background(.thinMaterial)
            }
            .navigationTitle("Halo Intelligence")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Dismiss") { dismiss() }
                }
            }
        }
    }
    
    private func executeAgentMessageSubmission() {
        let cleanPrompt = chatInputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleanPrompt.isEmpty else { return }
        
        chatHistoryList.append(("User", cleanPrompt))
        chatInputText = ""
        isAwaitingEngineReply = true
        
        Task {
            do {
                // Dynamically forwards the active local AppStorage profile identity 
                let modelReply = try await APIClient.shared.sendAgentChatMessage(
                    userId: userId,
                    message: cleanPrompt
                )
                
                DispatchQueue.main.async {
                    chatHistoryList.append(("Agent", modelReply))
                    isAwaitingEngineReply = false
                }
            } catch {
                DispatchQueue.main.async {
                    chatHistoryList.append(("Agent", "⚠️ Error connecting to Gemini MCP cluster service paths."))
                    isAwaitingEngineReply = false
                }
            }
        }
    }
}