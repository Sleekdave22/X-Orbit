# Ordered colour pairs

X_ORBIT version 11 (`0.11-x-orbit-colour-pairs`).

Each visible option is named **first / second**. The first colour is both the sent-message fill and active theme/button colour. The second colour is both the received-message fill and inactive button colour. Each side has its own readable foreground text colour; light colours no longer force white text.

Choices:

- Gold / Oxblood
- Oxblood / Gold
- Blue / Gold
- Red / Sky blue
- Green / Pink
- Pink / Matte black
- Purple / Lemon
- Matte black / Sky blue
- Sky blue / Oxblood

The Slate option and former descriptive one-colour names are removed. Retired saved palette IDs resolve to an appropriate current pair in the backend and Android cache, without deleting account preferences. No database schema changes are required.

Personalization previews sent/received messages and active/inactive button examples before saving. The selection remains account-specific across chat and Orbit Play. Save operations invalidate older preference reads so a delayed request cannot revert the newly saved pair; editing a selection is preserved during background refreshes. Android updates rendered bubbles/buttons without resetting the conversation or its draft.

Semantic answer/end call colours, wallpaper, icons, message contents, notification routing and GuardianLab protection are preserved.

Validation: account isolation, retired-selection compatibility, required colour labels, sender/theme equality and both sides' text contrast (4.5:1 minimum) pass. Browser account-switch tests pass. Synthetic browser checks confirm Blue / Gold gives blue sent messages/active buttons and gold received messages/inactive buttons. Android debug build and existing JVM tests pass.

Local deployment: the HTTPS browser server was updated and the live Personalization dialog verified with all nine choices and both role previews. Version 11 was installed on the S21 over Wi-Fi, retaining @s21 and its existing server/account configuration; authenticated profile, league and match endpoints remain available. Native visual appearance still needs user confirmation on the phone.
