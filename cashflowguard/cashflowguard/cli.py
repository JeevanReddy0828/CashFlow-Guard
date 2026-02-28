"""Command-line interface for CashFlowGuard."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from cashflowguard.analytics import (
    calculate_ar_summary,
    forecast_cash_inflows,
    get_aging_summary,
    simulate_cash_scenarios,
)
from cashflowguard.config import Config
from cashflowguard.io import DataLoader, save_actions, save_dataframe, validate_all
from cashflowguard.ml.predict import score_invoices
from cashflowguard.ml.train import LatePaymentModel, train_model
from cashflowguard.recommendations.engine import generate_recommendations
from cashflowguard.utils import logger, setup_logger

app = typer.Typer(
    help="CashFlowGuard - Invoice collections and cash flow management for SMBs"
)
console = Console()


@app.command()
def validate(
    data_dir: Path = typer.Option(
        Path("data/sample"),
        "--data-dir",
        "-d",
        help="Directory containing CSV files"
    )
) -> None:
    """Validate data files (customers.csv, invoices.csv, payments.csv)."""
    console.print("[bold blue]Validating data files...[/bold blue]")
    
    try:
        loader = DataLoader(data_dir)
        customers_df, invoices_df, payments_df, _ = loader.load_all(validate=True)
        
        console.print("[bold green]✓ All validations passed![/bold green]")
        console.print(f"  Customers: {len(customers_df)}")
        console.print(f"  Invoices: {len(invoices_df)}")
        console.print(f"  Payments: {len(payments_df) if payments_df is not None else 0}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Validation failed: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def analyze(
    data_dir: Path = typer.Option(Path("data/sample"), "--data-dir", "-d"),
    as_of: Optional[str] = typer.Option(None, "--as-of"),
    output_format: str = typer.Option("text", "--format", "-f"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o")
) -> None:
    """Analyze accounts receivable and generate report."""
    console.print("[bold blue]Analyzing accounts receivable...[/bold blue]")
    
    # Load data
    loader = DataLoader(data_dir)
    customers_df, invoices_df, payments_df, actions_df = loader.load_all()
    
    # Parse as_of date
    as_of_date = datetime.fromisoformat(as_of) if as_of else datetime.now()
    
    # Calculate AR summary
    ar_summary = calculate_ar_summary(invoices_df, payments_df)
    
    # Get aging summary
    aging_summary = get_aging_summary(invoices_df, as_of_date)
    
    # Display results
    if output_format in ["text", "all"]:
        _print_ar_summary(ar_summary, aging_summary)
    
    if output_format in ["json", "all"]:
        output = {
            "as_of": as_of_date.isoformat(),
            "ar_summary": ar_summary,
            "aging_summary": aging_summary.to_dict("records")
        }
        
        if output_file:
            with open(output_file, "w") as f:
                json.dump(output, f, indent=2)
            console.print(f"[green]Report saved to {output_file}[/green]")
        else:
            console.print_json(data=output)


@app.command()
def train(
    data_dir: Path = typer.Option(Path("data/sample"), "--data-dir", "-d"),
    model_dir: Path = typer.Option(Path("models"), "--model-dir", "-m"),
    model_type: str = typer.Option("gradient_boost", "--model-type"),
    test_size: float = typer.Option(0.25, "--test-size"),
    late_threshold: int = typer.Option(7, "--late-threshold")
) -> None:
    """Train late payment prediction model."""
    console.print("[bold blue]Training prediction model...[/bold blue]")
    
    # Load data
    loader = DataLoader(data_dir)
    customers_df, invoices_df, payments_df, _ = loader.load_all()
    
    if payments_df is None or len(payments_df) == 0:
        console.print("[red]Cannot train model without payment history[/red]")
        raise typer.Exit(1)
    
    # Train model
    model, metrics = train_model(
        invoices_df,
        customers_df,
        payments_df,
        model_type=model_type,
        late_threshold_days=late_threshold,
        test_size=test_size
    )
    
    # Save model
    model_path = model_dir / f"model_{model_type}.pkl"
    model.save(model_path)
    
    # Save metrics
    metrics_path = model_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    
    console.print(f"[green]✓ Model trained and saved to {model_path}[/green]")
    console.print(f"  Test accuracy: {metrics['test_accuracy']:.4f}")
    console.print(f"  CV ROC-AUC: {metrics['cv_roc_auc_mean']:.4f}")


@app.command()
def score(
    data_dir: Path = typer.Option(Path("data/sample"), "--data-dir", "-d"),
    model_dir: Path = typer.Option(Path("models"), "--model-dir", "-m"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o")
) -> None:
    """Score open invoices for late payment risk."""
    console.print("[bold blue]Scoring invoices...[/bold blue]")
    
    # Load data
    loader = DataLoader(data_dir)
    customers_df, invoices_df, payments_df, _ = loader.load_all()
    
    # Load or use fallback
    model_path = model_dir / "model_gradient_boost.pkl"
    
    # Score invoices
    scored_df = score_invoices(
        invoices_df,
        customers_df,
        payments_df,
        model_path=model_path if model_path.exists() else None
    )
    
    # Show top risky invoices
    risky = scored_df[scored_df["status"] == "open"].sort_values(
        "risk_score", ascending=False
    ).head(20)
    
    _print_risk_scores(risky)
    
    # Save if requested
    if output_file:
        save_dataframe(scored_df, output_file, "scored invoices")


@app.command()
def plan(
    data_dir: Path = typer.Option(Path("data/sample"), "--data-dir", "-d"),
    model_dir: Path = typer.Option(Path("models"), "--model-dir", "-m"),
    week: str = typer.Option(None, "--week"),
    top: int = typer.Option(30, "--top"),
    tone: str = typer.Option("friendly", "--tone")
) -> None:
    """Generate weekly collections plan."""
    console.print("[bold blue]Generating collections plan...[/bold blue]")
    
    # Load data
    loader = DataLoader(data_dir)
    customers_df, invoices_df, payments_df, actions_df = loader.load_all()
    
    # Score invoices
    model_path = model_dir / "model_gradient_boost.pkl"
    scored_df = score_invoices(
        invoices_df,
        customers_df,
        payments_df,
        model_path=model_path if model_path.exists() else None
    )
    
    # Generate recommendations
    recommendations = generate_recommendations(
        scored_df,
        customers_df,
        actions_df
    )
    
    # Get top N
    top_recommendations = recommendations.head(top)
    
    _print_collections_plan(top_recommendations, tone)


@app.command()
def simulate(
    data_dir: Path = typer.Option(Path("data/sample"), "--data-dir", "-d"),
    scenarios: int = typer.Option(100, "--scenarios"),
    days: int = typer.Option(30, "--days")
) -> None:
    """Simulate cash flow scenarios."""
    console.print("[bold blue]Running cash flow simulation...[/bold blue]")
    
    # Load data
    loader = DataLoader(data_dir)
    customers_df, invoices_df, payments_df, _ = loader.load_all()
    
    # Run simulation
    results = simulate_cash_scenarios(
        invoices_df,
        payments_df,
        n_scenarios=scenarios,
        days_ahead=days
    )
    
    # Display results
    console.print(f"\n[bold]Cash Flow Simulation ({scenarios} scenarios, {days} days)[/bold]")
    console.print(f"  P10 (pessimistic): ${results['total_collected'].quantile(0.1):,.2f}")
    console.print(f"  P50 (median):      ${results['total_collected'].median():,.2f}")
    console.print(f"  P90 (optimistic):  ${results['total_collected'].quantile(0.9):,.2f}")
    console.print(f"  Mean:              ${results['total_collected'].mean():,.2f}")


@app.command()
def action(
    invoice: str = typer.Option(..., "--invoice"),
    action_type: str = typer.Option(..., "--type"),
    notes: str = typer.Option("", "--notes"),
    data_dir: Path = typer.Option(Path("data/sample"), "--data-dir", "-d")
) -> None:
    """Record a collection action taken."""
    from cashflowguard.storage.actions_store import record_action
    
    # Load actions
    loader = DataLoader(data_dir)
    actions_df = loader.load_actions()
    
    # Record action
    new_action = record_action(
        invoice_id=invoice,
        action_type=action_type,
        notes=notes,
        outcome="pending"
    )
    
    # Append to actions
    actions_df = pd.concat([actions_df, pd.DataFrame([new_action])], ignore_index=True)
    
    # Save
    save_actions(actions_df, data_dir)
    
    console.print(f"[green]✓ Action recorded for {invoice}[/green]")


def _print_ar_summary(summary: dict, aging: pd.DataFrame) -> None:
    """Print AR summary."""
    console.print("\n[bold]Accounts Receivable Summary[/bold]")
    console.print(f"  Total AR:           ${summary['total_ar']:,.2f}")
    console.print(f"  Overdue AR:         ${summary['overdue_ar']:,.2f} ({summary['overdue_percentage']:.1f}%)")
    console.print(f"  DSO:                {summary['dso']:.1f} days")
    console.print(f"  Collection Rate:    {summary.get('payment_rate', 0):.1f}%")
    
    # Aging table
    table = Table(title="\nAging Breakdown")
    table.add_column("Bucket")
    table.add_column("Amount", justify="right")
    table.add_column("%", justify="right")
    table.add_column("Count", justify="right")
    
    for _, row in aging.iterrows():
        table.add_row(
            row["aging_bucket"],
            f"${row['total_amount']:,.0f}",
            f"{row['percentage']:.1f}%",
            str(int(row["invoice_count"]))
        )
    
    console.print(table)


def _print_risk_scores(df: pd.DataFrame) -> None:
    """Print risk scores table."""
    table = Table(title="Top Risky Invoices")
    table.add_column("Invoice")
    table.add_column("Customer")
    table.add_column("Amount", justify="right")
    table.add_column("Risk", justify="right")
    table.add_column("Category")
    
    for _, row in df.head(20).iterrows():
        table.add_row(
            row["invoice_id"],
            row.get("customer_id", "")[:20],
            f"${row['invoice_amount']:,.0f}",
            f"{row.get('risk_score', 0):.0f}",
            row.get("risk_category", "unknown")
        )
    
    console.print(table)


def _print_collections_plan(df: pd.DataFrame, tone: str) -> None:
    """Print collections plan."""
    console.print(f"\n[bold]Collections Plan ({len(df)} invoices)[/bold]")
    
    table = Table()
    table.add_column("#", justify="right")
    table.add_column("Invoice")
    table.add_column("Customer")
    table.add_column("Amount", justify="right")
    table.add_column("Days OD", justify="right")
    table.add_column("Risk", justify="right")
    table.add_column("Action")
    
    for idx, row in df.head(30).iterrows():
        table.add_row(
            str(idx + 1),
            row["invoice_id"],
            row.get("name", "")[:25],
            f"${row['invoice_amount']:,.0f}",
            str(int(row.get("days_overdue", 0))),
            f"{row.get('risk_score', 0):.0f}",
            row.get("recommended_action", "")
        )
    
    console.print(table)


if __name__ == "__main__":
    app()
