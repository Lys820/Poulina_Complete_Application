namespace PouleLabApp.API.Models
{
    // Phases du workflow pour lesquelles une échéance peut être définie
    public enum DeadlinePhase
    {
        Reception,
        Assignment,
        Analysis,
        Validation,
        ResultDelivery
    }
}