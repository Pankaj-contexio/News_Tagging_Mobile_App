# News Tagging Mobile App

This directory contains a React Native (Expo) mobile application that interfaces with the existing Flask backend for news tagging.

## Prerequisites
- Node.js (>= 18)
- Expo CLI: `npm install -g expo-cli`
- Android Studio or Xcode for emulators (optional)

## Setup
1. Copy `.env.example` to `.env` and update the `API_BASE_URL` to point to your Flask backend.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm start
   ```
4. Run on Android emulator/device:
   ```bash
   npm run android
   ```
   Run on iOS simulator/device:
   ```bash
   npm run ios
   ```

## Connecting to Flask Backend
The app expects the Flask backend to expose endpoints like `/login`, `/dashboard`, `/news`, `/news/<id>/tags`, and `/reports`. Authentication uses JWT tokens returned from `/login`.

Ensure your Flask server is running and accessible at the URL configured in `.env`.

## Testing
Run basic tests:
```bash
npm test
```

## Debugging Tips
- Use Expo dev tools in the browser for logs and inspecting network requests.
- Monitor backend logs to trace API calls.
- Use React Native Debugger or Flipper for inspecting Redux state and AsyncStorage.

## Building for Production
```bash
expo build:android   # or expo build:ios
```

## Push Notifications
The app uses `expo-notifications` to request notification permissions. Configure Expo push notifications to receive alerts for new articles.
