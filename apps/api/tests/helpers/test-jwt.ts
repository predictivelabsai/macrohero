import { generateKeyPair, SignJWT, exportJWK, type KeyLike } from "jose";

export interface TestJwtSetup {
  privateKey: KeyLike;
  publicKey: KeyLike;
  jwks: { keys: Array<Record<string, unknown>> };
  issuer: string;
  mintToken(opts: { sub: string; ttlSeconds?: number; issuer?: string }): Promise<string>;
}

export async function setupTestJwt(): Promise<TestJwtSetup> {
  const { privateKey, publicKey } = await generateKeyPair("RS256");
  const publicJwk = await exportJWK(publicKey);
  publicJwk.use = "sig";
  publicJwk.alg = "RS256";
  publicJwk.kid = "test-key-1";

  const jwks = { keys: [publicJwk as unknown as Record<string, unknown>] };
  const issuer = "https://test.clerk.test";

  return {
    privateKey,
    publicKey,
    jwks,
    issuer,
    async mintToken({ sub, ttlSeconds = 3600, issuer: iss }) {
      return new SignJWT({})
        .setProtectedHeader({ alg: "RS256", kid: "test-key-1" })
        .setSubject(sub)
        .setIssuer(iss ?? issuer)
        .setIssuedAt()
        .setExpirationTime(`${ttlSeconds}s`)
        .sign(privateKey);
    },
  };
}
