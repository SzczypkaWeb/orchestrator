import asyncio
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions

BACKEND_PATH = str(Path('../backend').resolve())

TASK = """
Pracujesz w repo backend (Nest.js + Prisma). Wykonaj po kolei:

1. git checkout main && git pull, potem stwórz nowy branch: feat/delete-user-endpoint.
2. Dodaj endpoint DELETE /users/:id w UsersController, wywołujący nową metodę
   remove(id: string) w UsersService, która usuwa użytkownika przez
   this.prisma.user.delete({ where: { id } }).
3. Dodaj test w users.controller.spec.ts sprawdzający, że endpoint wywołuje
   service.remove z poprawnym id.
4. Uruchom `pnpm test` i upewnij się, że wszystko przechodzi. Jeśli coś nie
   przechodzi, popraw i uruchom ponownie.
5. Zrób commit z opisową wiadomością (conventional commits).
6. Wypchnij branch (git push -u origin feat/delete-user-endpoint) i otwórz PR:
   gh pr create --base main --head feat/delete-user-endpoint --fill
7. Na końcu wypisz krótkie podsumowanie i link do PR.
"""


async def main():
  async for message in query(
    prompt=TASK,
    options=ClaudeAgentOptions(
      cwd=BACKEND_PATH,
      allowed_tools=["Read", "Edit", "Write", "Bash", "Glob", "Grep" ],
      model="claude-sonnet-5",
    )
  ): 
    if hasattr(message, "result"):
      print(message.result)

asyncio.run(main())