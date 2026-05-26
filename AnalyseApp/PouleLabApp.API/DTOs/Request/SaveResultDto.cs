namespace PouleLabApp.API.DTOs.Request
{
    // Données envoyées par le laborantin pour saisir un résultat d'analyse
    public class SaveResultDto
    {
        public int    ResultId     { get; set; }
        public double MeasuredValue{ get; set; }
        public double LowerBound   { get; set; }   // Laborantin définit les bornes
        public double UpperBound   { get; set; }
        public string Unit         { get; set; } = string.Empty;
    }
}