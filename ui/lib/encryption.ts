const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY || 'your-encryption-key-here';
const ALGORITHM = 'AES-CBC';
const IV_LENGTH = 16;

async function getKey(): Promise<CryptoKey> {
  const keyData = new TextEncoder().encode(ENCRYPTION_KEY);
  const hash = await crypto.subtle.digest('SHA-256', keyData);
  return await crypto.subtle.importKey('raw', hash, ALGORITHM, false, ['encrypt', 'decrypt']);
}

export async function encrypt(text: string): Promise<string> {
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
}

export async function decrypt(text: string): Promise<string> {
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
} 