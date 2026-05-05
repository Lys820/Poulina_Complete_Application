namespace PouleLabApp.API.DTOs.Request
{
    // Données envoyées par le laborantin pour saisir un résultat d'analyse
    public class SaveResultDto
    {
        public int ResultId { get; set; }       // ID du résultat à remplir (créé vide à la création de la demande)
        public double MeasuredValue { get; set; } // Valeur mesurée par le laborantin
    }
}