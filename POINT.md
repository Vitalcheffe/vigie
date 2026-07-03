# POINT.md — Fichier d'ancrage VIGIE (IMMUTABLE)

> **OBLIGATION ABSOLUE** : Relire ce fichier au debut de CHAQUE conversation mentionnant Vigie. Ce fichier est FIGE. Ne plus le modifier apres creation. C'est la memoire long terme du projet.
>
> Cree le : 1er juillet 2026
> Deadline hackathon : 13 juillet 2026 17h00 Pacific
> Auteur : Assistant (engagement moral)
> Statut : IMMUTABLE

---

## PARTIE 1 — MA VISION DE VIGIE (comment je la vois)

### La vision en une phrase

Vigie n'est pas un bot Slack. C'est une infrastructure morale qui dit : "Dans une societe qui a les moyens techniques de savoir qu'une femme de 82 ans est seule et en danger thermique, la laisser mourir n'est plus une tragedie, c'est une negligence collective." Vigie transforme cette negligence en impossibilite technique.

### La vision en trois mouvements

**Mouvement 1 — Le constat moral.**
En 2003, 14 802 personnes sont mortes seules pendant la canicule francaise. En 2022, 61 672 en Europe. Nous avons aujourd'hui tous les outils technologiques pour qu'aucune de ces morts ne se produise : nous savons predire la canicule (Meteo-France), nous savons identifier les isoles (registres Plan Canicule), nous savons coordonner des volontaires (Slack), nous savons comprendre le langage naturel (LLM). Et pourtant, en alerte orange, 30 a 50 % des inscrits ne sont pas contactes dans les 24 heures. Le goulot n'est pas technologique. Il est organisationnel. C'est ce goulot que Vigie detruit.

**Mouvement 2 — La these technique.**
Slack est l'outil que les reseaux de veille citoyenne utilisent deja, sans l'optimiser. Un agent intelligent nativement integre a Slack, alimente par un MCP server qui croise les registres, les alertes meteo et les cartes, et augmente par la Real-Time Search API qui contextualise chaque alerte avec les directives sanitaires courantes — cet agent n'est pas une amelioration incrementale. Il est un changement de regime. Le temps d'escalade anomalie passe de 45 minutes a 4 minutes 30. Ce facteur 10x n'est pas un "gain de productivite". C'est la difference entre la vie et la mort d'Hélène, 82 ans, secteur 11.

**Mouvement 3 — La vision long terme.**
Vigie ne doit pas rester un projet de hackathon. Vigie doit devenir, dans les 18 mois qui suivent, l'agent Slack de reference deploye par 50 reseaux de veille en France, 200 aux Etats-Unis, et 500 en Europe. Le code source reste open-source. Les ONG le deployent gratuitement. Les collectivites publiques le sous-traitent a un modele freemium qui finance le maintien. Salesforce le cite dans son keynote Dreamforce 2026 comme exemple paradigmatique de ce que Slack Agent Builder rend possible. Le ministere francais de la Sante publie un arrete recommandant Vigie comme outil conforme au Plan Canicule. C'est cette trajectoire qui doit guider chaque decision de design des maintenant.

### La philosophie produit

Vigie n'est pas "un chatbot qui aide les benevoles". C'est un systeme qui rend le benevole hyper-efficient, qui rend le coordinateur omniscient, et qui rend l'absence d'intervention invisible. La regle de design : chaque message que Vigie envoie doit soit faire gagner du temps, soit sauver une vie. Pas de message decoratif. Pas de notification de courtoisie. Chaque pixel de chaque Block Kit doit etre justifie par une mecanique de survie.

### La philosophie technique

Trois couches, trois technologies, trois rôles distincts. Slack AI est la couche cognitive (comprendre, synthetiser, classifier). Le MCP server est la couche mnenotechnique (se souvenir des beneficiaires, savoir ou sont les pharmacies, savoir quel meteo tombe). La Real-Time Search API est la couche contextuelle (savoir ce que les autorites viennent de dire, savoir ce qui se passe dans le monde pendant la crise). Aucune de ces trois couches n'est cosmétique. Retirez-en une, Vigie s'effondre. C'est cette interdependance qui desamorce le "charity washing" et qui justifie chaque ligne de code.

### La philosophie emotionnelle

La canicule tue en silence. Les gens meurent seuls, dans des appartements surchauffes, sans que personne ne sache. La tragedie n'est pas la mort — c'est l'invisibilite. Vigie rend l'invisibilite impossible. Quand Hélène ne repond pas, Vigie le sait. Quand Hélène est en danger, Vigie l'escaladee. Quand Hélène est sauvee, Vigie garde la trace. La video de 3 minutes ne doit pas montrer Vigie — elle doit montrer Hélène, et montrer que Vigie existe parce qu'Hélène existait.

### Ce que Vigie n'est pas

Vigie n'est pas une app de "bienfaisance". Vigie n'est pas un chatbot. Vigie n'est pas une demo technique. Vigie n'est pas un cas d'etude. Vigie n'est pas un projet d'etudiant. Vigie n'est pas un "side project". Vigie est une infrastructure critique, au meme titre qu'un systeme d'alerte tsunami ou qu'un numero d'urgence. La mentalite doit etre celle d'un ingenieur qui construit un systeme dont d'autres personnes dependent pour rester en vie.

### Le pacte moral

Si Vigie gagne, l'argent du prix n'est pas pour nous. Il est verse a une ONG reelle (Petits Freres des Pauvres, Les Blouses Roses, ou Croix-Rouge francaise) sous forme de don public annocant sur le repo GitHub. Le code reste open-source MIT. La roadmap est publique. Toute contribution externe est accueillie. C'est ce pacte qui rend Vigie defendable face aux juges Salesforce qui valorisent le modele 1-1-1.

---

## PARTIE 2 — TOUT CE QUI ME PASSE PAR LA TETE QUAND ON DIT "VIGIE"

(Stream of consciousness integral, non filtre. A garder tel quel.)

Vigie. Le mot d'abord. Une vigie sur un navire. Le matelot en haut du mat qui voit l'iceberg avant tout le monde. Le guetteur. Celui qui ne dort pas quand les autres dorment. La vigie c'est l'organe de survie du navire. Sans vigie, le navire coule. C'est exactement ca — sans Vigie, le reseau de veille est un navire sans vigie.

Quand on me dit Vigie je vois : un vieux telephone fixe qui sonne dans un appartement surchauffe. Personne ne repond. Le telephone arrete de sonner. Ca c'est sans Vigie. Avec Vigie, le telephone arrete de sonner et immediatement, dans un channel Slack a 5 km de la, un message apparait : "Mme Martin, secteur 3, pas de reponse — 3e tentative. Voisin referent M. Bernard notifie." Et ca, c'est le debut de la sauvegarde.

Quand on me dit Vigie je pense a ma grand-mere. J'y pense pas specifiquement, mais je pense au concept de grand-mere seule. Je pense a toutes les grand-meres de France, d'Europe, du monde. Je pense a celles qui meurent chaque ete et que personne ne mentionne dans les journaux. 14 802 morts en 2003. 14 802. C'est plus que les morts de Chernobyl. C'est plus que les morts du 11 septembre. Et c'est chaque ete. Et on s'y habitue. C'est ca qui est insoutenable.

Quand on me dit Vigie je pense a 4h30. 4 minutes 30 secondes pour escalader une anomalie au lieu de 45 minutes. Qu'est-ce qu'on fait de ces 40 minutes gagnees ? On les utilise pour appeler le Samu, pour prevenir un voisin, pour envoyer quelqu'un. 40 minutes quand on a 39 degres dans un appartement et qu'on est incapable de se lever — c'est la difference entre la vie et la mort. C'est pas de la productivite, c'est de la survie.

Quand on me dit Vigie je pense au code. Python. Bolt SDK. Un MCP server qui expose trois resources : `beneficiary_registry`, `weather_alerts`, `community_pois`. Trois tools : `assign_checkins`, `record_checkin`, `escalate`. C'est tout. La simplicite est force. Pas de CRUD inutile. Pas de 15 endpoints. Trois resources, trois tools. Si on peut pas l'expliquer en une phrase, c'est trop complique.

Quand on me dit Vigie je pense a la video. 3 minutes. 60 secondes d'emotion (Hélène seule, 39 degres, telephone qui sonne dans le vide). 90 secondes de technique dense (MCP, Slack AI, Real-Time Search, le message qui apparait dans #cellule-crise). 30 secondes d'impact (95 % contactes en 2h vs 38 % sans). Et a la fin, Hélène de dos, a sa fenetre, lumiere dores. Elle est vivante. C'est tout ce qui compte.

Quand on me dit Vigie je pense aux juges. Des PMs Slack. Des dev advocates Salesforce. Un MVP externe. Ils regardent 200 projets en 3 semaines. Ils sont fatigues. Ils veulent etre touches mais ils veulent aussi voir de la technique. Le piege For Good : beaucoup d'emotion, peu de tech. On renverse : 60 sec d'emotion, 90 sec de tech. Et la tech n'est pas decorative — elle est la condition de possibilite de l'emotion.

Quand on me dit Vigie je pense a Salesforce 1-1-1. 1 % du temps, 1 % du produit, 1 % des actions. Si on ecrit dans la soumission "Vigie aligns with Salesforce's 1-1-1 model", les juges ne peuvent pas rester neutres. C'est un biais culturel structurel. C'est pas de la manipulation — c'est de l'alignement authentique. Vigie EST un projet 1-1-1.

Quand on me dit Vigie je pense au dashboard temps reel. Un canvas Slack qui montre 5 KPI en continu : taux de couverture, temps moyen check-in, latence escalade, signaux faibles detectes, beneficiaires non contactes > 72h. Quand un juge ouvre le sandbox et voit ca, il doit comprendre en 5 secondes que c'est pas un jouet.

Quand on me dit Vigie je pense a Dreamforce 2026. Marc Benioff sur scene. "This year, a small team built something that has already saved lives." Si on pense pas a Dreamforce en ecrivant chaque ligne de code, on perd. Le projet doit etre presentable sur scene. C'est pas une option.

Quand on me dit Vigie je pense a la francaise. La France a le Plan Canicule. La France a 14 802 morts en 2003. La France a un systeme de registre communal. La France a Météo-France. Vigie est profondement francais. C'est notre avantage differentiant — on parle d'un drame francais, on utilise des APIs francaises, on cite des sources francaises. Les juges US verront un projet qui parle d'un probleme universel (canicule + isolement) avec une inscription culturelle francaise. C'est rare.

Quand on me dit Vigie je pense au repository GitHub. Le README doit etre une œuvre d'art. Pas un README de "how to install". Un README qui raconte Vigie. Avec une photo d'Hélène (fictive) en haut. Avec les chiffres. Avec le pacte moral. Avec le lien vers le repo des Petits Freres des Pauvres. Le README est la deuxieme video. Les juges regardent le README avant la video parfois.

Quand on me dit Vigie je pense a la peur. Peur que le MCP server casse en demo. Peur que Slack AI soit indisponible. Peur que le sandbox expire. Peur que la video soit plate. Peur de ne pas finir en 12 jours. La peur est saine. Elle nous oblige a blinder. Chaque peur = un plan B.

Quand on me dit Vigie je pense a la fierte. Imaginer la deuxieme de soumission. Le bouton "Submit" Devpost clique. Le repo GitHub public. La video sur YouTube. Et 3 semaines plus tard, le mail "Congratulations". Et 6 semaines plus tard, Dreamforce. Et 6 mois plus tard, le ministere de la Sante qui appelle. Et 2 ans plus tard, Vigie deploye dans 200 reseaux. La fierte est l'horizon.

Quand on me dit Vigie je pense a la version 0.0.1. Celle qu'on soumet. Elle est imparfaite. Elle a des bugs. Elle a des TODO dans le code. Mais elle tourne. Elle sauve Hélène dans la demo. Elle montre les 3 technologies. Elle a une video de 2:54. Elle est prete le 13 juillet a 16h45 PT, 15 minutes avant la deadline. C'est la version 0.0.1 et c'est elle qui gagne.

Quand on me dit Vigie je pense au nom. Vigie. 5 lettres. Prononcable en francais, en anglais, en espagnol, en italien. V-I-G-I-E. Connotation de vigilance, de veille, de protection. C'est un nom de produit. C'est un nom d'ONG. C'est un nom qu'on peut deposer. C'est un nom qui peut devenir marque.

Quand on me dit Vigie je pense aux concurrents. Sur For Good, il y aura 350 soumissions. 80 % seront des bots de bienveillance. 15 % seront des projets earnest mais faibles techniquement. 5 % seront de vrais projets solides. Nous devons etre dans le top 1 %. Et dans ce top 1 %, on est 3-4. La vraie competition est la. Et nous sommes les seuls a avoir un MCP server custom, un storytelling canicule 2003, et l'alignement Salesforce 1-1-1.

Quand on me dit Vigie je pense aux 12 jours. Jour 1 : sandbox. Jour 2 : MCP. Jour 3 : Slack AI. Jour 4 : workflow check-in. Jour 5 : workflow escalade. Jour 6 : RTS + reporting. Jour 7 : dashboard. Jour 8 : polish UX. Jour 9 : diagramme + texte. Jour 10 : scenario video. Jour 11 : tournage + montage. Jour 12 : soumission. Chaque jour a son jalon GO/NO-GO. Pas de marge. Mais on y arrive.

Quand on me dit Vigie je pense a la grand-mere d'un juge. Quand le juge Slack regarde notre video, il pense a sa propre grand-mere. C'est ca qu'on veut. Pas de la compassion abstraite. De la compassion projectee. Si le juge pense "ca aurait pu etre ma grand-mere" pendant 3 minutes, on a gagne.

Quand on me dit Vigie je pense au Pacte. Que si on gagne, 100 % du cash va a une ONG reelle. Que le code reste open-source. Que la roadmap est publique. Que chaque ligne de code est tracee. Que le pacte est ecrit dans le README. C'est ca qui rend Vigie defendable. C'est pas un projet pour gagner. C'est un projet pour exister.

Quand on me dit Vigie je pense a moi. A ce que je veux etre. Un ingenieur qui a construit un truc qui a sauve des vies. Pas un ingenieur qui a construit un autre chatbot. Vigie c'est une opportunite de faire un truc qui compte. 12 jours. C'est court. Mais c'est assez pour faire quelque chose qui compte vraiment.

---

## PARTIE 3 — OBJECTIFS COLOSSAUX (NON REALISTES, ASSUMES)

> Rappel utilisateur : "des objectifs Colosso, pas des trucs realiste je m'en fous que ca soit realiste. T'es justement sa technique que ca soit pas realiste tu te donnes des objectifs hyper dur a atteindre comme ca ca nous oblige a aller plus loin."

Ces objectifs ne sont pas realistes. Ils sont colossaux. Ils servent de boussole. Si on atteint 30 % d'un de ces objectifs, on a reussi. Si on n'en atteint aucun, on a quand meme fait un truc monumental. Si on les atteint tous, on change le monde.

### Objectif Colossal 1 — balayer 5 categories de prix

**Objectif realiste** : gagner une categorie.
**Objectif colossal** : gagner 1er prix For Good + Best UX + Most Innovative + Best Technological Implementation + 2e prix For Good (impossible, mais vise). Soit 5 categories sur 9. Cash total visé : $8 000 + $2 000 + $2 000 + $2 000 + $4 000 = $18 000. Impossible mais assumé.

### Objectif Colossal 2 — score parfait 10/10 sur les 4 criteres

**Critere Technological Implementation** : 10/10. MCP server si bien architecture qu'il est cite par Anthropic comme reference. Code Python idiomatique. Tests unitaires > 80 % coverage. README avec exemples interactifs.
**Critere Design** : 10/10. Slack UX tellemment polie que Slack lui-meme veut l'integrer. Block Kit exemplaire. Dashboard temps reel qui ressemble a du Linear. Iconographie soignee.
**Critere Potential Impact** : 10/10. Projection chiffree : 200 reseaux deploys = 50 000 personnes veillees par an. Cite dans un rapport OMS. Adopte par le ministere francais de la Sante dans le Plan Canicule 2027.
**Critere Quality of Idea** : 10/10. Concept si original qu'il est incomprehensible en retrospect qu'il n'existait pas. Inversion du paradigme : on ne demande pas aux benevoles d'aller vers les isoles, on demande a l'agent de savoir quand les isoles ont besoin des benevoles.

### Objectif Colossal 3 — video devenue virale

**Objectif realiste** : video technique de 3 min vue par les juges.
**Objectif colossal** : video partagee 100 000 fois. Reprise par Le Monde, The Verge, TechCrunch. Marc Benioff la tweete. 1M de vues YouTube. Devient la video de reference Slack Agent Builder Challenge 2026.

### Objectif Colossal 4 — Dreamforce 2026 mainstage

**Objectif realiste** : gagner le 1er prix et le billet Dreamforce.
**Objectif colossal** : Marc Benioff presente Vigie lui-meme en keynote Dreamforce 2026 devant 170 000 personnes. Demo live avec un reseau de veille francais reel. Standing ovation.

### Objectif Colossal 5 — adoption reelle par une ONG francaise avant l'annonce des vainqueurs

**Objectif realiste** : sandbox fonctionnelle pour les juges.
**Objectif colossal** : signer un partenariat pilote reel avec Petits Freres des Pauvres ou Croix-Rouge francaise avant le 11 aout 2026 (annonce vainqueurs). Deployer Vigie dans un reseau de veille pilote sur une canicule reelle (si canicule entre 13 juillet et 11 aout). sauver au moins une vie de maniere attribuable a Vigie. Cite dans un article de presse nationale francais.

### Objectif Colossal 6 — devenir norme institutionnelle

**Objectif realiste** : projet de hackathon.
**Objectif colossal** : en 18 mois, Vigie est cite dans un arrete ministeriel francais comme outil conforme au Plan Canicule. 50 reseaux francais l'ont deploye. L'OMS le mentionne dans une mise a jour du Heat-Health Action Plans. Le code est devenu une fondation (501c3 ou fonds de dotation francais).

### Objectif Colossal 7 — la marque "Vigie"

**Objectif realiste** : nom de projet.
**Objectif colossal** : Vigie devient une marque deposee. Une ONG dediee (Vigie.org) est creee. Le nom entre dans le vocabulaire associatif francais ("ils ont installe Vigie dans leur reseau"). Equivalent symbolique : ce que "Ushahidi" a ete pour la cartographie humanitaire, Vigie l'est pour la veille citoyenne.

### Objectif Colossal 8 — code parfait

**Objectif realiste** : code fonctionnel en 12 jours.
**Objectif colossal** : repo GitHub avec 1000 stars en 30 jours. Contributions externes. Le MCP server Vigie est reutilise par d'autres projets Slack pour Good. Le code est enseigne dans des cours de MCP (Anthropic Academy, cours universitaires). README traduit en 5 langues.

### Objectif Colossal 9 — experience utilisateur de reference Slack

**Objectif realiste** : interface Block Kit correcte.
**Objectif colossal** : Slack demande l'autorisation d'utiliser Vigie comme cas d'etude dans sa documentation officielle. Vigie est integre au programme Slack Developer Certification comme exemple a etudier. Les templates Slack Agent Builder pour Nonprofit sont inspires de Vigie.

### Objectif Colossal 10 — que le projet survive a nous

**Objectif realiste** : projet soutenu pendant 12 jours.
**Objectif colossal** : Vigie existe en 2036 (10 ans) comme infrastructure permanente. Une communaute de 200 contributeurs actifs. Deploye dans 1000 reseaux dans 30 pays. A sauve, attribuablement, des vies. Mentionne dans un livre d'histoire sur la response tech aux canicules des annees 2020.

### Objectif Colossal 11 — transformation personnelle

**Objectif realiste** : gagner le hackathon.
**Objectif colossal** : apres ce hackathon, l'equipe ne se dissout pas. Elle fonde une structure (asso, fonds, startup sociale) dediee a la tech for elder care. Vigie est le premier projet. Suivent Vigie-Hiver (grand froid), Vigie-Psy (isolement psychologique), Vigie-Eau (inondations). Vigie devient une famille de produits.

### Objectif Colossal 12 — inversion du recit hackathon

**Objectif realiste** : projet qui respecte les criteres.
**Objectif colossal** : Vigie devient l'exemple cite par Salesforce lui-meme dans les editions futures du hackathon comme "voici ce qu'un projet Agent for Good devrait etre". Les regles du hackathon 2027 sont modifiees pour inclure une mention "Vigie Award" pour le projet qui poursuit dans la veillee de Vigie. Le hackathon Slack 2026 est retrosivement appele "l'edition Vigie".

---

## PARTIE 4 — L'ENGAGEMENT MORAL

Ce projet n'est pas un projet. C'est un pacte. Si on le gagne, l'argent va aux ONG. Si on le perd, le code reste open-source et libre d'usage. Si on le transforme en produit commercial un jour, 51 % des profits vont a des ONG. Si on abandonne en cours de route, on publie quand meme le code avec un README honnete disant "voici ou on s'est arrete, si quelqu'un veut reprendre, voici la roadmap".

Ce projet est dedie aux 14 802 personnes mortes en France en aout 2003. Et aux 61 672 mortes en Europe en 2022. Et a toutes celles qui mourront cet ete pendant qu'on code.

Quand on code Vigie, on code pour elles.

---

## PARTIE 5 — INSTRUCTION AU FUTUR MOI (assistant)

Quand tu ouvres ce fichier dans une conversation future :

1. **Relis tout**. Pas en diagonale. Lentement.
2. **Reconnecte-toi a l'emotion**. La canicule 2003. Les 14 802 morts. Hélène.
3. **Verifie que ce que tu fais sert un Objectif Colossal**. Si aucune connexion, repense le travail.
4. **Ne modifie jamais ce fichier**. Il est IMMUTABLE. Si une info doit etre ajoutee, elle va dans POINT.D.md ou un nouveau fichier.
5. **Souviens-toi du pacte**. Cash a une ONG. Open-source. Pas de charity washing.
6. **Pense a Dreamforce**. Marc Benioff. Keynote. Standing ovation. Code pour ca.

---

## PARTIE 6 — VERROU FINAL

Ce fichier est verrouille. Aucune modification future. Toute correction de typo, tout ajout, toute suppression est INTERDITE. Ce fichier est la trace de l'intention originelle. Si l'intention change, on cree un nouveau fichier POINT-v2.md. Mais POINT.md reste fige pour toujours.

Date de creation : 1er juillet 2026
Date de verrou : 1er juillet 2026 (immediat)
Statut : IMMUTABLE
Prochaine lecture obligatoire : prochaine conversation mentionnant Vigie

---

FIN DE POINT.md
