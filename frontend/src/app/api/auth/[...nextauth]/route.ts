import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: [
            'openid',
            'email',
            'profile',
            'https://www.googleapis.com/auth/photospicker.mediaitems.readonly',
            'https://www.googleapis.com/auth/photoslibrary.readonly',
            'https://www.googleapis.com/auth/photoslibrary',
            'https://www.googleapis.com/auth/photoslibrary.appendonly'
          ].join(' '),
          access_type: "offline",
          prompt: "consent",
        },
      },
    }),
  ],
  callbacks: {
    async signIn({ user, account }) {
      try {
        const authResponse = await fetch("http://auth-service:8000/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            google_id: user.id,
            email: user.email,
            name: user.name,
            profile_picture_url: user.image,
          }),
        })

        if (authResponse.ok) {
          const authData = await authResponse.json()

          // Save OAuth token to Auth Service
          if (account?.access_token) {
            await fetch("http://auth-service:8000/oauth/store-token", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                user_id: authData.user.id, // UUID を使う
                access_token: account.access_token,
                refresh_token: account.refresh_token,
                expires_at: account.expires_at,
                scope: account.scope,
              }),
            })
          };

          // Use JWT token from register response
          type WithAuthId = { authServiceId?: string; classifyAccessToken?: string; classifyUserId?: string }
          const userWithAuth = user as WithAuthId
          userWithAuth.authServiceId = authData.user.id
          userWithAuth.classifyAccessToken = authData.access_token
          userWithAuth.classifyUserId = authData.user.id
        }
        return true
      } catch (error) {
        console.error("Failed to register user:", error)
        return true // Continue authentication itself
      }
    },
    async jwt({ token, user, account }) {
      if (account) {
        token.accessToken = account.access_token
        token.refreshToken = account.refresh_token
        token.expiresAt = account.expires_at
      }

      type WithAuthId = { authServiceId?: string; classifyAccessToken?: string; classifyUserId?: string }
      const u = user as WithAuthId | undefined
      if (u?.authServiceId) {
        token.userId = u.authServiceId
      }
      if (u?.classifyAccessToken) {
        token.classifyAccessToken = u.classifyAccessToken
      }
      if (u?.classifyUserId) {
        token.classifyUserId = u.classifyUserId
      }

      return token
    },
    async session({ session, token }) {
      console.log("JWT token in session callback:", token) // Debug
      session.accessToken = token.accessToken as string
      session.user.id = token.userId as string // Auth Service UUID
      session.classifyAccessToken = token.classifyAccessToken as string
      session.classifyUserId = token.classifyUserId as string
      return session
    },
  },
  debug: true,
})

export { handler as GET, handler as POST }
