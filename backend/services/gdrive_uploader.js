const fs = require('fs');
const path = require('path');
const { google } = require(path.join(process.cwd(), 'node_modules', 'googleapis'));
const dotenv = require('dotenv');

// Robust dotenv load
const envPaths = [
  path.join(process.cwd(), '.env', '.env'),
  path.join(process.cwd(), 'backend', '.env'),
  path.join(process.cwd(), '.env')
];
for (const p of envPaths) {
  if (fs.existsSync(p)) {
    dotenv.config({ path: p });
  }
}

/**
 * Uploads a video file or stream to Google Drive using googleapis Node.js client.
 * Uses GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN, and GDRIVE_FOLDER_ID.
 */
async function uploadToGoogleDrive({ filePath, fileBuffer, fileName, mimeType = 'video/mp4' }) {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  const redirectUri = process.env.GOOGLE_REDIRECT_URI || 'https://developers.google.com/oauthplayground';
  const refreshToken = process.env.GOOGLE_REFRESH_TOKEN;
  const folderId = process.env.GDRIVE_FOLDER_ID || '19GL0-JhadO0fRXlRzVS5tFTQ1_2pKbD1';

  if (!clientId || !clientSecret || !refreshToken) {
    throw new Error('Missing Google OAuth credentials in environment.');
  }

  const oauth2Client = new google.auth.OAuth2(clientId, clientSecret, redirectUri);
  oauth2Client.setCredentials({ refresh_token: refreshToken });

  const drive = google.drive({ version: 'v3', auth: oauth2Client });

  let readableStream;
  if (filePath) {
    readableStream = fs.createReadStream(filePath);
  } else if (fileBuffer) {
    const { Readable } = require('stream');
    readableStream = Readable.from(fileBuffer);
  } else {
    throw new Error('Either filePath or fileBuffer must be provided.');
  }

  const fileMetadata = {
    name: fileName,
    parents: [folderId]
  };

  const media = {
    mimeType: mimeType,
    body: readableStream
  };

  const response = await drive.files.create({
    resource: fileMetadata,
    media: media,
    fields: 'id, name, webViewLink, webContentLink'
  });

  return {
    file_id: response.data.id,
    filename: response.data.name,
    webViewLink: response.data.webViewLink
  };
}

module.exports = {
  uploadToGoogleDrive
};

// CLI execution check
if (require.main === module) {
  console.log('Mindscape Node.js Google Drive uploader initialized successfully.');
}
