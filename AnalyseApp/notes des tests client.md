* pour chaque filiale/marque, une liste déroulante d'échantillon en fonction de chaque marque
* Liste déroulante pour la section des unités pour éviter les erreurs de saisie
* pour les échéances, l'ordre des étapes doit aller de haut en bas et non de gauche à droite (le 2 au dessous du 1 pas à sa droite)
* Pour l'assignation il faut régler l'affichage ( le nom/prénom et l'email du laborantin sont collés )
* Pour les notifications, lorsque la donnée de la notification est ouverte hors onglet notification, la notification doit être automatiquement marquée comme lue (par exemple, si la réceptionniste a reçue une nouvelle demande d'analyse et qu'elle l'a ouvert et consulté dans le tableau de bord, la notification de cette demande en question doit automatiquement être marquée comme lue dans l'onglet "notifications"
* Pour les notifications, si une notification a été consulté dans l'onglet notifications, celle ci doit être automatiquement marquée comme lue, faut pas attendre que ce soit fait manuellement en cliquant sur la notification.
* dans le tableau de bords, on peut consulter une demande d'analyse en l'ouvrant et ce en cliquant n'importe où dessus

&#x20;



* Client :
* Tests Création de demande :

  * 1 - Créer une demande complète et la soumettre : Statut submitted mais pas d'email de confirmation reçu --> Pas de notification
  * 4 - Soumettre sans sélectionner de labo : Message d'erreur "Erreur lors de l'enregistrement" et soumission bloquée --> il faut mettre un message d'erreur clair
  * 6 - Création d'une demande identique à une déjà en cours : Fonctionne partiellement --> tout doit être vérifié sauf les notes et les observations car ils peuvent être différents d'une personne à l'autre lors de la soumission d'une demande.



* Tests des échéances :

  * 3 - Suppression d'une échéance individuelle : Visuellement l'échéance est supprimé mais lorsque je souhaite modifier les échéances, celle ci est présente avec l'heure et la date renseignées avant sa suppression --> Il faut que les champs date et heures d'une échéance supprimée soient vides lorsque je souhaite modifier les échéances
  * 6 - Définition d'échéances avec une date/heure passée : L'enregistrement de l'échéance est bloqué mais aucun message d'erreur ne s'affiche.



* Tests de consultations :

  * 6 - Voir les notifications : Aucune notifications n'a été reçue
  * 7 - Marquer une notification comme lue : étant donné qu'aucune notification n'est reçue, je ne peux pas marquer de notifs comme lues
  * 8 - Supprimer toutes les notifications : étant donné qu'aucune notification n'est reçue, je ne peux pas supprimer de notifs

