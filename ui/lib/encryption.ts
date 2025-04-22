const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY || 'your-encryption-key-here';
const ALGORITHM = 'AES-CBC';
const IV_LENGTH = 16;

// Simple XOR encryption for development
function simpleEncrypt(text: string): string {
  const key = ENCRYPTION_KEY;
  let result = '';
  for (let i = 0; i < text.length; i++) {
    result += String.fromCharCode(text.charCodeAt(i) ^ key.charCodeAt(i % key.length));
  }
  return btoa(result);
}

function simpleDecrypt(text: string): string {
  const key = ENCRYPTION_KEY;
  const decoded = atob(text);
  let result = '';
  for (let i = 0; i < decoded.length; i++) {
    result += String.fromCharCode(decoded.charCodeAt(i) ^ key.charCodeAt(i % key.length));
  }
  return result;
}

async function getKey(): Promise<CryptoKey> {
  const keyData = new TextEncoder().encode(ENCRYPTION_KEY);
  const hash = await crypto.subtle.digest('SHA-256', keyData);
  return await crypto.subtle.importKey('raw', hash, ALGORITHM, false, ['encrypt', 'decrypt']);
}

export async function encrypt(text: string): Promise<string> {
  // Check if crypto.subtle is available
  if (!crypto.subtle) {
    return simpleEncrypt(text);
  }

  try {
    const key = await getKey();
    const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH));
    const encodedText = new TextEncoder().encode(text);
    
    const encryptedData = await crypto.subtle.encrypt(
      { name: ALGORITHM, iv },
      key,
      encodedText
    );
    
    const encryptedArray = new Uint8Array(encryptedData);
    const result = new Uint8Array(iv.length + encryptedArray.length);
    result.set(iv);
    result.set(encryptedArray, iv.length);
    
    return btoa(Array.from(result).map(byte => String.fromCharCode(byte)).join(''));
  } catch (error) {
    console.warn('Web Crypto API failed, falling back to simple encryption:', error);
    return simpleEncrypt(text);
  }
}

export async function decrypt(text: string): Promise<string> {
  // Check if crypto.subtle is available
  if (!crypto.subtle) {
    return simpleDecrypt(text);
  }

  try {
    const key = await getKey();
    const data = Uint8Array.from(atob(text), c => c.charCodeAt(0));
    const iv = data.slice(0, IV_LENGTH);
    const encrypted = data.slice(IV_LENGTH);
    
    const decryptedData = await crypto.subtle.decrypt(
      { name: ALGORITHM, iv },
      key,
      encrypted
    );
    
    return new TextDecoder().decode(decryptedData);
  } catch (error) {
    console.warn('Web Crypto API failed, falling back to simple decryption:', error);
    return simpleDecrypt(text);
  }
} 