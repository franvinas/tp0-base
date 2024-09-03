package common

type Bet struct {
	Agency    string
	Name      string
	Surname   string
	Document  string
	BirthDate string
	Number    string
}

func (bet Bet) Encode() string {
	return bet.Agency + "," + bet.Name + "," + bet.Surname + "," + bet.Document + "," + bet.BirthDate + "," + bet.Number + "\n"
}
