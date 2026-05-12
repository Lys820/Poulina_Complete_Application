namespace PouleLabApp.API.Models
{
    // Statuts possibles d'une demande — suit le workflow défini dans le cahier des charges
    public enum RequestStatus
    {
        Draft,      // Brouillon non encore soumis
        Submitted,  // Soumis par le client, en attente de réception
        Received,   // Réceptionné et enregistré par le réceptionniste
        Assigned,   //assigné, en attente d'acceptation du laborantin
        InProgress, // Acceepté par un laborantin, analyses en cours
        InReview,   // Analyses terminées, en attente de validation du chef de labo
        Validated,  // Résultats validés, disponibles pour le client
        Rejected,   // Rejeté par le chef de labo, renvoyé à la réception
        Closed      // Clôturé (refus définitif)
    }
}