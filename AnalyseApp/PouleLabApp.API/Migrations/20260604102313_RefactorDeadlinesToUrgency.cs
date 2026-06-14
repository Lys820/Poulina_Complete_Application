using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PouleLabApp.API.Migrations
{
    /// <inheritdoc />
    public partial class RefactorDeadlinesToUrgency : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Deadlines_Samples_SampleId",
                table: "Deadlines");

            migrationBuilder.DropColumn(
                name: "PlannedDate",
                table: "Deadlines");

            migrationBuilder.RenameColumn(
                name: "Phase",
                table: "Deadlines",
                newName: "UrgencyLevel");

            migrationBuilder.RenameColumn(
                name: "IsOverdue",
                table: "Deadlines",
                newName: "IsPerishable");

            migrationBuilder.RenameColumn(
                name: "ActualDate",
                table: "Deadlines",
                newName: "ExpiryDate");

            migrationBuilder.AlterColumn<int>(
                name: "SampleId",
                table: "Deadlines",
                type: "int",
                nullable: false,
                defaultValue: 0,
                oldClrType: typeof(int),
                oldType: "int",
                oldNullable: true);

            migrationBuilder.AddColumn<string>(
                name: "UrgencyDescription",
                table: "Deadlines",
                type: "nvarchar(max)",
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddForeignKey(
                name: "FK_Deadlines_Samples_SampleId",
                table: "Deadlines",
                column: "SampleId",
                principalTable: "Samples",
                principalColumn: "Id",
                onDelete: ReferentialAction.Restrict);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Deadlines_Samples_SampleId",
                table: "Deadlines");

            migrationBuilder.DropColumn(
                name: "UrgencyDescription",
                table: "Deadlines");

            migrationBuilder.RenameColumn(
                name: "UrgencyLevel",
                table: "Deadlines",
                newName: "Phase");

            migrationBuilder.RenameColumn(
                name: "IsPerishable",
                table: "Deadlines",
                newName: "IsOverdue");

            migrationBuilder.RenameColumn(
                name: "ExpiryDate",
                table: "Deadlines",
                newName: "ActualDate");

            migrationBuilder.AlterColumn<int>(
                name: "SampleId",
                table: "Deadlines",
                type: "int",
                nullable: true,
                oldClrType: typeof(int),
                oldType: "int");

            migrationBuilder.AddColumn<DateTime>(
                name: "PlannedDate",
                table: "Deadlines",
                type: "datetime2",
                nullable: false,
                defaultValue: new DateTime(1, 1, 1, 0, 0, 0, 0, DateTimeKind.Unspecified));

            migrationBuilder.AddForeignKey(
                name: "FK_Deadlines_Samples_SampleId",
                table: "Deadlines",
                column: "SampleId",
                principalTable: "Samples",
                principalColumn: "Id");
        }
    }
}
