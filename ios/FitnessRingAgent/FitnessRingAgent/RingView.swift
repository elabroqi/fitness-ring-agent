import SwiftUI

struct RingView: View {
    // Dynamic parameters ready to be hooked to your FastAPI backend
    @State private var batteryLevel: Int = 74
    @State private var ringName: String = "Oura Ring 4"
    @State private var ringMaterial: String = "Ceramic"
    @State private var activeUser: String = "aurela"
    @State private var sizeMetric: Int = 8
    
    var body: some View {
        ZStack {
            // =====================================================================
            // 1. BACKGROUND LAYER: Atmospheric Portrait Blend
            // =====================================================================
            GeometryReader { geo in
                ZStack {
                    Color.black // Base backing
                    
                    // Main aesthetic profile imagery
                    Image(systemName: "person.crop.rectangle.stack") // Placeholder asset
                        .resizable()
                        .scaledToFill()
                        .frame(width: geo.size.width, height: geo.size.height)
                        .opacity(0.35)
                        .blur(radius: 2)
                    
                    // Smooth overhead lighting vignette
                    LinearGradient(
                        gradient: Gradient(colors: [
                            Color.blue.opacity(0.2),
                            Color.clear,
                            Color.black.opacity(0.6)
                        ]),
                        startPoint: .top,
                        endPoint: .bottom
                    )
                }
                .ignoresSafeArea()
            }
            
            // =====================================================================
            // 2. FOREGROUND CONTENT LAYER
            // =====================================================================
            VStack(spacing: 0) {
                
                // --- Top Vitals Array ---
                VStack(alignment: .leading, spacing: 4) {
                    Text("Battery Life")
                        .font(.system(size: 14, weight: .medium, design: .rounded))
                        .foregroundColor(.white.opacity(0.6))
                    
                    HStack(alignment: .firstTextBaseline, spacing: 4) {
                        Text("\(batteryLevel)%")
                            .font(.system(size: 40, weight: .semibold, design: .rounded))
                            .foregroundColor(.white)
                        
                        Text("Optimal")
                            .font(.system(size: 14, weight: .medium, design: .rounded))
                            .foregroundColor(.green)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.top, 40)
                .padding(.horizontal, 30)
                
                Spacer()
                
                // --- Central Arc Tracking Display ---
                ZStack {
                    // Thin background track arc
                    Circle()
                        .trim(from: 0.2, to: 0.8)
                        .stroke(Color.white.opacity(0.15), style: StrokeStyle(lineWidth: 3, lineCap: .round))
                        .rotationEffect(.degrees(90))
                        .frame(width: 300, height: 300)
                    
                    // Active battery trace level glow arc
                    Circle()
                        .trim(from: 0.2, to: 0.2 + (0.6 * (Double(batteryLevel) / 100.0)))
                        .stroke(
                            LinearGradient(colors: [.white, .white.opacity(0.4)], startPoint: .top, endPoint: .bottom),
                            style: StrokeStyle(lineWidth: 3, lineCap: .round)
                        )
                        .rotationEffect(.degrees(90))
                        .frame(width: 300, height: 300)
                        .shadow(color: .white.opacity(0.3), radius: 8, x: 0, y: 0)
                }
                .padding(.bottom, 20)
                
                Spacer()
                
                // =====================================================================
                // 3. THE FROSTED GLASS CONSOLE PANEL (Matching your blueprint)
                // =====================================================================
                VStack(spacing: 25) {
                    // Small alignment chevron
                    Image(systemName: "chevron.compact.down")
                        .font(.system(size: 18, weight: .medium))
                        .foregroundColor(.white.opacity(0.3))
                        .padding(.top, 8)
                    
                    // Device Information Metadata Row
                    HStack(alignment: .center) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(ringName)
                                .font(.system(size: 18, weight: .semibold, design: .rounded))
                                .foregroundColor(.white)
                            Text(ringMaterial)
                                .font(.system(size: 14, weight: .regular, design: .rounded))
                                .foregroundColor(.white.opacity(0.5))
                        }
                        
                        Spacer()
                        
                        // Hardware Avatar Center (Your Ring Rendering Layout)
                        ZStack {
                            Circle()
                                .fill(Color.white.opacity(0.08))
                                .frame(width: 80, height: 80)
                            
                            Image(systemName: "record.circle") // Swap with your beautiful ring asset image
                                .font(.system(size: 55, weight: .ultraLight))
                                .foregroundColor(.white.opacity(0.85))
                        }
                        
                        Spacer()
                        
                        VStack(alignment: .trailing, spacing: 4) {
                            Text("Cloud Status")
                                .font(.system(size: 12, weight: .medium, design: .rounded))
                                .foregroundColor(.white.opacity(0.4))
                            Text("Saved")
                                .font(.system(size: 14, weight: .medium, design: .rounded))
                                .foregroundColor(.blue)
                            Text("Battery \(batteryLevel)%")
                                .font(.system(size: 11, weight: .regular, design: .rounded))
                                .foregroundColor(.white.opacity(0.3))
                        }
                    }
                    .padding(.horizontal, 25)
                    
                    // Pod Control Interface Dock (Size | Activate Capsule | Battery)
                    HStack(spacing: 0) {
                        // Left Capsule: Hardware Size Metric
                        VStack(spacing: 2) {
                            Text("\(sizeMetric)")
                                .font(.system(size: 20, weight: .bold, design: .rounded))
                                .foregroundColor(.black)
                            Text("Size")
                                .font(.system(size: 10, weight: .medium))
                                .foregroundColor(.black.opacity(0.4))
                        }
                        .frame(width: 60, height: 60)
                        .background(Circle().fill(Color.white))
                        
                        // Center Capsule: System Activation Action
                        Button(action: {
                            print("Triggering background telemetry synchronization loop...")
                        }) {
                            Text("Activate")
                                .font(.system(size: 15, weight: .semibold, design: .rounded))
                                .foregroundColor(.black)
                                .frame(width: 140, height: 60)
                                .background(Capsule().fill(Color.white))
                        }
                        .padding(.horizontal, -10) // Locks capsules tight against one another
                        
                        // Right Capsule: Battery Sync Readout
                        VStack(spacing: 2) {
                            Text("\(batteryLevel)")
                                .font(.system(size: 20, weight: .bold, design: .rounded))
                                .foregroundColor(.black)
                            Text("Battery")
                                .font(.system(size: 10, weight: .medium))
                                .foregroundColor(.black.opacity(0.4))
                        }
                        .frame(width: 60, height: 60)
                        .background(Circle().fill(Color.white))
                    }
                    .padding(.bottom, 35)
                }
                .frame(maxWidth: .infinity)
                // Appends Apple's native structural blurs directly behind your interface metrics
                .background(.ultraThinMaterial)
                .environment(\.colorScheme, .dark) // Enforces dark mode styling on blur layers
                .cornerRadius(40, corners: [.topLeft, .topRight])
            }
        }
    }
}

// Helper extension to mask corner radius selections uniquely
extension View {
    func cornerRadius(_ radius: CGFloat, corners: UIRectCorner) -> some View {
        clipShape(RoundedCorner(radius: radius, corners: corners))
    }
}

struct RoundedCorner: Shape {
    var radius: CGFloat = .infinity
    var corners: UIRectCorner = .allCorners

    func path(in rect: CGRect) -> Path {
        let path = UIBezierPath(roundedRect: rect, byRoundingCorners: corners, cornerRadii: CGSize(width: radius, height: radius))
        return Path(path.cgPath)
    }
}

#Preview {
    RingView()
}