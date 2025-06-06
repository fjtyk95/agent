import subprocess
from pathlib import Path


def test_cli_runs(tmp_path: Path) -> None:
    master = tmp_path / "bank_master.csv"
    fee = tmp_path / "fee_table.csv"
    balance = tmp_path / "balance_snapshot.csv"
    cash = tmp_path / "cashflow_history.csv"
    out = tmp_path / "plan.csv"

    master.write_text("bank_id,branch_id,service_id,cut_off_time\nB1,B1,S1,16:00\nB2,B1,S1,16:00\n")
    fee.write_text(
        "from_bank,from_branch,service_id,amount_bin,to_bank,to_branch,fee\n"
        "B1,B1,S1,0+,B2,B1,1\n"
        "B2,B1,S1,0+,B1,B1,1\n"
    )
    balance.write_text("bank_id,balance\nB1,100\nB2,100\n")
    cash.write_text(
        "date,bank_id,amount,direction\n"
        "2021-01-01,B1,10,out\n"
        "2021-01-01,B2,10,in\n"
    )

    cmd = [
        "python",
        "-m",
        "bankoptimize",
        "run",
        "--master",
        str(master),
        "--fee",
        str(fee),
        "--balance",
        str(balance),
        "--cash",
        str(cash),
        "--out",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert out.exists()
