namespace PouleLabApp.API.Services.Interfaces
{
    // Contrat du service de génération PDF
    // Deux types de documents : formulaire de demande et bulletin de résultats
    public interface IPdfService
    {
        // PDF du formulaire de demande — disponible dès la soumission
        byte[] GenerateRequestFormPdf(int requestId);

        // PDF du bulletin d'analyses — disponible uniquement après validation
        byte[] GenerateBulletinPdf(int requestId);
    }
}