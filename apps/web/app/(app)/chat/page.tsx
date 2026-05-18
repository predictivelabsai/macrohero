import { currentUser } from "@clerk/nextjs/server";

import { timeOfDayGreeting } from "@/lib/greeting";
import { getMe } from "@/lib/me";

import { ChatUI } from "./chat-ui";

// `/chat` is the empty "new chat" state. The session is created lazily on
// the first user message — see /api/chat/start.
//
// First name comes from Clerk (auto-populated from Google/social profile or
// the required email-signup field). Timezone lives in our DB.
export default async function ChatIndexPage() {
  const [user, me] = await Promise.all([currentUser(), getMe()]);
  return (
    <ChatUI
      sessionId={null}
      initialMessages={[]}
      displayName={user?.firstName ?? null}
      greeting={timeOfDayGreeting(me.timezone)}
    />
  );
}
