const localtunnel = require('localtunnel');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

async function deploy() {
  console.log("🚀 Initiating Zero-Intervention Cloud Deployment...");

  try {
    // 1. Tunnel the Backend (FastAPI on 8000)
    console.log("📡 Tunneling Backend (Port 8000)...");
    const backendTunnel = await localtunnel({ port: 8000 });
    console.log(`✅ Backend Cloud URL: ${backendTunnel.url}`);

    // 2. Inject Cloud URL into Frontend
    console.log("💉 Injecting Cloud URL into React App...");
    const appJsxPath = path.join(__dirname, 'landing-page', 'src', 'App.jsx');
    let appJsx = fs.readFileSync(appJsxPath, 'utf8');
    
    // Regex to replace const API = 'http://localhost:8000'; or similar
    appJsx = appJsx.replace(/const API = ['"`].*?['"`];/, `const API = '${backendTunnel.url}';`);
    fs.writeFileSync(appJsxPath, appJsx);
    console.log("✅ Frontend configured to use Cloud Backend.");

    // 3. Build Frontend
    console.log("🏗️ Building Production Frontend...");
    execSync('npm run build', { cwd: path.join(__dirname, 'landing-page'), stdio: 'inherit' });
    console.log("✅ Build Complete.");

    // 4. Serve the Build Directory on a new port (e.g., 3000) using npx serve
    console.log("🌐 Starting Production Server on Port 3000...");
    // We run serve in the background. It serves the dist folder.
    // Using powershell start-process so it doesn't block this script.
    execSync('start /B npx serve -s dist -l 3000', { cwd: path.join(__dirname, 'landing-page'), stdio: 'ignore' });
    
    // Wait a second for serve to start
    await new Promise(r => setTimeout(r, 2000));

    // 5. Tunnel the Frontend (Port 3000)
    console.log("📡 Tunneling Frontend (Port 3000)...");
    const frontendTunnel = await localtunnel({ port: 3000 });
    console.log(`\n🎉 DEPLOYMENT SUCCESSFUL 🎉\n`);
    console.log(`=================================================`);
    console.log(`🌍 PUBLIC FRONTEND URL: ${frontendTunnel.url}`);
    console.log(`⚙️  PUBLIC BACKEND URL: ${backendTunnel.url}`);
    console.log(`=================================================`);
    console.log(`Share the Frontend URL with anyone. Keep this script running to maintain the tunnels.`);

    // Handle tunnel closure
    backendTunnel.on('close', () => console.log('Backend tunnel closed'));
    frontendTunnel.on('close', () => console.log('Frontend tunnel closed'));

    // Keep process alive
    process.stdin.resume();

  } catch (error) {
    console.error("❌ Deployment Failed:", error);
    process.exit(1);
  }
}

deploy();
