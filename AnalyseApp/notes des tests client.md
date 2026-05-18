* pour chaque filiale/marque, une liste déroulante d'échantillon en fonction de chaque marque
* Liste déroulante pour la section des unités pour éviter les erreurs de saisie
* pour les échéances, l'ordre des étapes doit aller de haut en bas et non de gauche à droite (le 2 au dessous du 1 pas à sa droite)
* Pour l'assignation il faut régler l'affichage ( le nom/prénom et l'email du laborantin sont collés )

&#x20;





* Tests Création de demande :

  * 1 - Créer une demande complète et la soumettre : Statut submitted mais pas d'email de confirmation reçu --> Pas de notification
  * 4 - Soumettre sans sélectionner de labo : Message d'erreur "Erreur lors de l'enregistrement" et soumission bloquée --> il faut mettre un message d'erreur clair
  * 6 - Création d'une demande identique à une déjà en cours : Fonctionne partiellement --> tout doit être vérifié sauf les notes et les observations car ils peuvent être différents d'une personne à l'autre lors de la soumission d'une demande.



* Tests des échéances :

  * 3 - Suppression d'une échéance individuelle : Visuellement l'échéance est supprimé mais lorsque je souhaite modifier les échéances, celle ci est présente avec l'heure et la date renseignées avant sa suppression --> Il faut que les champs date et heures d'une échéance supprimée soient vides lorsque je souhaite modifier les échéances
  * 6 - Définition d'échéances avec une date/heure passée : L'enregistrement de l'échéance est bloqué mais aucun message d'erreur ne s'affiche.



* Tests de consultations :

  * 6 - Voir les notifications : Aucune notifications n'a été reçue

