import type { DefaultSession } from 'next-auth'

declare module 'next-auth' {
  interface User {
    authServiceId?: string
  }
  interface Session {
    user: {
      id: string
    } & DefaultSession['user']
    accessToken?: string
    classifyAccessToken?: string
    classifyUserId?: string
  }
}

declare module 'next-auth/adapters' {
  interface AdapterUser {
    authServiceId?: string
  }
}

declare module 'next-auth/core/types' {
  interface User {
    authServiceId?: string
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken?: string
    refreshToken?: string
    classifyAccessToken?: string
    classifyUserId?: string
  }
}
