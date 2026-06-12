import SwiftUI

struct RingView: View {
    @AppStorage("user_id") private var userId: String = ""

    @StateObject private var bluetooth = RingDiscoveryManager()

    @State private var boundRing: DiscoveredRing?
    @State private var isBinding = false
    @State private var statusMessage: String?
    @State private var dashboard: DashboardResponse?

    private var batteryLevel: Int {
        dashboard?.batteryLevel ?? 0
    }

    private var ringName: String {
        dashboard?.connectedDeviceName ?? "No Ring Bound"
    }

    private var ringMaterial: String {
        dashboard?.deviceType ?? "Scan to connect"
    }

    private var sizeMetric: Int {
        7
    }

    var body: some View {
        ZStack {
            GeometryReader { geo in
                ZStack {
                    Color.black

                    Image(systemName: "person.crop.rectangle.stack")
                        .resizable()
                        .scaledToFill()
                        .frame(width: geo.size.width, height: geo.size.height)
                        .opacity(0.35)
                        .blur(radius: 2)

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

            VStack(spacing: 0) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Ring Status")
                        .font(.system(size: 14, weight: .medium, design: .rounded))
                        .foregroundColor(.white.opacity(0.6))

                    HStack(alignment: .firstTextBaseline, spacing: 4) {
                        Text(ringName == "No Device Bound" ? "Not Bound" : "Bound")
                            .font(.system(size: 36, weight: .semibold, design: .rounded))
                            .foregroundColor(.white)

                        Text(bluetooth.bluetoothState)
                            .font(.system(size: 14, weight: .medium, design: .rounded))
                            .foregroundColor(bluetooth.bluetoothState == "On" ? .green : .orange)
                    }

                    if let statusMessage {
                        Text(statusMessage)
                            .font(.caption)
                            .foregroundColor(.white.opacity(0.7))
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.top, 40)
                .padding(.horizontal, 30)

                Spacer()

                ZStack {
                    Circle()
                        .trim(from: 0.2, to: 0.8)
                        .stroke(Color.white.opacity(0.15), style: StrokeStyle(lineWidth: 3, lineCap: .round))
                        .rotationEffect(.degrees(90))
                        .frame(width: 300, height: 300)

                    Circle()
                        .trim(from: 0.2, to: 0.2 + (0.6 * (Double(batteryLevel) / 100.0)))
                        .stroke(
                            LinearGradient(colors: [.white, .white.opacity(0.4)], startPoint: .top, endPoint: .bottom),
                            style: StrokeStyle(lineWidth: 3, lineCap: .round)
                        )
                        .rotationEffect(.degrees(90))
                        .frame(width: 300, height: 300)
                        .shadow(color: .white.opacity(0.3), radius: 8, x: 0, y: 0)

                    VStack(spacing: 8) {
                        Image(systemName: "record.circle")
                            .font(.system(size: 64, weight: .ultraLight))
                            .foregroundColor(.white.opacity(0.85))

                        Text(ringName)
                            .font(.headline)
                            .foregroundColor(.white)

                        Text(ringMaterial)
                            .font(.caption)
                            .foregroundColor(.white.opacity(0.55))
                    }
                }
                .padding(.bottom, 20)

                Spacer()

                VStack(spacing: 20) {
                    Image(systemName: "chevron.compact.down")
                        .font(.system(size: 18, weight: .medium))
                        .foregroundColor(.white.opacity(0.3))
                        .padding(.top, 8)

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

                        ZStack {
                            Circle()
                                .fill(Color.white.opacity(0.08))
                                .frame(width: 80, height: 80)

                            Image(systemName: "dot.radiowaves.left.and.right")
                                .font(.system(size: 42, weight: .ultraLight))
                                .foregroundColor(.white.opacity(0.85))
                        }

                        Spacer()

                        VStack(alignment: .trailing, spacing: 4) {
                            Text("Cloud Status")
                                .font(.system(size: 12, weight: .medium, design: .rounded))
                                .foregroundColor(.white.opacity(0.4))

                            Text(ringName == "No Device Bound" ? "Not Saved" : "Saved")
                                .font(.system(size: 14, weight: .medium, design: .rounded))
                                .foregroundColor(boundRing == nil ? .orange : .blue)

                            Text("Battery \(batteryLevel)%")
                                .font(.system(size: 11, weight: .regular, design: .rounded))
                                .foregroundColor(.white.opacity(0.3))
                        }
                    }
                    .padding(.horizontal, 25)

                    Button {
                        if bluetooth.isScanning {
                            bluetooth.stopScan()
                        } else {
                            bluetooth.startScan()
                        }
                    } label: {
                        Text(bluetooth.isScanning ? "Scanning..." : "Scan for Ring")
                            .font(.system(size: 15, weight: .semibold, design: .rounded))
                            .foregroundColor(.black)
                            .frame(maxWidth: .infinity)
                            .frame(height: 52)
                            .background(Capsule().fill(Color.white))
                    }
                    .padding(.horizontal, 25)
                    .disabled(bluetooth.bluetoothState != "On" || isBinding)
                    
                    HStack(spacing: 0) {
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

                        Button {
                            Task {
                                await toggleRingBinding()
                            }
                        } label: {
                            Text(ringName == "No Device Bound" ? "Bind Ring" : "Unbind Ring")
                                .font(.system(size: 15, weight: .semibold, design: .rounded))
                                .foregroundColor(.black)
                                .frame(width: 140, height: 60)
                                .background(Capsule().fill(Color.white))
                        }
                        .padding(.horizontal, -10)

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

                    if ringName != "No Device Bound" {
                        Button("Connect Different Ring") {
                            // open DeviceBindingView
                        }
                        .foregroundColor(.white)
                    }
                }
                .frame(maxWidth: .infinity)
                .background(.ultraThinMaterial)
                .environment(\.colorScheme, .dark)
                .cornerRadius(40, corners: [.topLeft, .topRight])
            }
        }
        .task {
            await loadDashboard()
        }
    }

    private func bind(_ ring: DiscoveredRing) async {
        isBinding = true
        statusMessage = nil

        do {
            try await APIClient.shared.bindDevice(
                userId: userId,
                deviceName: ring.name,
                peripheralUUID: ring.id.uuidString,
                deviceType: ring.name
            )

            boundRing = ring
            statusMessage = "Ring bound successfully."
            bluetooth.stopScan()

            await loadDashboard()
        } catch {
            statusMessage = "Could not bind ring."
        }

        isBinding = false
    }

    private func loadDashboard() async {
        do {
            dashboard = try await APIClient.shared.fetchDashboard(userId: userId)
        } catch {
            statusMessage = "Could not load ring data."
        }
    }

    private func toggleRingBinding() async {
        if ringName != "No Device Bound" {
            // Unbind flow
            statusMessage = "Unbinding..."
            isBinding = true
            do {
                try await APIClient.shared.unbindDevice(userId: userId)
                boundRing = nil
                dashboard = nil
                statusMessage = "Ring unbound successfully."
                await loadDashboard()
            } catch {
                statusMessage = "Could not unbind ring."
            }
            isBinding = false
            return
        }

        // Existing binding flow
        statusMessage = "Searching for ring..."
        isBinding = true

        bluetooth.startScan()
        try? await Task.sleep(for: .seconds(2))
        bluetooth.stopScan()

        guard let ring = bluetooth.discoveredRings.first else {
            statusMessage = "No ring found nearby."
            isBinding = false
            return
        }

        await bind(ring)
        isBinding = false
    }
}


extension View {
    func cornerRadius(_ radius: CGFloat, corners: UIRectCorner) -> some View {
        clipShape(RoundedCorner(radius: radius, corners: corners))
    }
}

struct RoundedCorner: Shape {
    var radius: CGFloat = .infinity
    var corners: UIRectCorner = .allCorners

    func path(in rect: CGRect) -> Path {
        let path = UIBezierPath(
            roundedRect: rect,
            byRoundingCorners: corners,
            cornerRadii: CGSize(width: radius, height: radius)
        )
        return Path(path.cgPath)
    }
}

#Preview {
    RingView()
}
