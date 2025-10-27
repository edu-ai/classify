'use client'

import { useSession, signIn, signOut } from 'next-auth/react'

export default function AuthButton() {
  const { data: session, status } = useSession()

  console.log('Session status:', status)
  console.log('Session data:', session)

  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center space-x-2">
        <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        <span>Loading...</span>
      </div>
    )
  }

  if (session) {
    return (
      <div className="flex items-center space-x-4">
        <button
          onClick={() => signOut()}
          className="w-full px-3 py-2 bg-red-500 hover:bg-red-600 text-white font-bold rounded"
        >
          Sign Out
        </button>
      </div>
    )
  }

  return (
    <button
      onClick={() => {
        console.log('Sign in button clicked')
        signOut({ redirect: false })
        signIn('google', { prompt: "consent", callbackUrl: '/' })
      }}
      className="w-full px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white font-bold rounded"
    >
      Sign in with Google
    </button>
  )
}
