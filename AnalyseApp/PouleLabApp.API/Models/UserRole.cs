namespace PouleLabApp.API.Models
{
    // Rôles disponibles dans l'application
    public enum UserRole
    {
        Administrator, // Accès total
        Manager,       // Gestion des utilisateurs et rapports
        Receptionist,  // Réception et affectation des demandes
        Analyst,       // Saisie des résultats d'analyse
        LabChief,      // Validation des résultats
        Client         // Soumission des demandes
    }
}